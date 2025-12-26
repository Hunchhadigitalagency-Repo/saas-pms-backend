import re
import json
import logging

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny

from work_items.models import WorkItems, Status
from project.models import Project, ProjectActivityLog
from project.adapters.serializers.project_activity_log_serializer import ProjectActivityLogSerializer
from utils.custom_paginator import CustomPaginator
from pms.jwt_auth import CookieJWTAuthentication

logger = logging.getLogger(__name__)

# ----------------------------
# Regex Patterns
# ----------------------------

# WI-47:#start | TASK-12:#done
EXPLICIT_TASK_STATUS_REGEX = re.compile(
    r'\b[A-Z]+-(?P<id>\d+)\s*:\s*#(?P<status>[a-zA-Z_]+)\b',
    re.IGNORECASE
)

# WI-47 WI-48 TASK-9
TASK_ID_REGEX = re.compile(
    r'\b[A-Z]+-(?P<id>\d+)\b',
    re.IGNORECASE
)

# #start #done (global)
GLOBAL_STATUS_REGEX = re.compile(
    r'#(?P<status>pending|start|inprogress|done|complete|closed)',
    re.IGNORECASE
)

# ----------------------------
# Status Mapping (MATCHES MODEL)
# ----------------------------

STATUS_MAP = {
    "pending": Status.PENDING,
    "start": Status.IN_PROGRESS,
    "inprogress": Status.IN_PROGRESS,
    "done": Status.COMPLETED,
    "complete": Status.COMPLETED,
    "closed": Status.COMPLETED,
}

FINAL_BRANCHES = {"main", "master", "production"}


def resolve_status(keyword: str):
    return STATUS_MAP.get(keyword.lower())


def is_status_allowed(branch: str, new_status: str) -> bool:
    """
    Rule:
    - ONLY main/master/production can set COMPLETED
    - pending / in_progress allowed everywhere
    """
    if new_status == Status.COMPLETED:
        return branch in FINAL_BRANCHES
    return True


# ----------------------------
# ViewSet
# ----------------------------

class ProjectActivityLogViewSet(viewsets.ModelViewSet):
    """
    Project Activity Log API
    """
    serializer_class = ProjectActivityLogSerializer
    pagination_class = CustomPaginator
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        return ProjectActivityLog.objects.all().order_by("-created_at")

    @action(detail=False, methods=["get"], url_path="by-project/(?P<project_id>[^/.]+)")
    def get_activity_by_project_id(self, request, project_id=None):
        queryset = ProjectActivityLog.objects.filter(
            project__id=project_id
        ).order_by("-created_at")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # ----------------------------
    # GitHub Webhook
    # ----------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="post-push-event",
        permission_classes=[AllowAny],
        authentication_classes=[]
    )
    def post_push_event(self, request, pk=None):
        try:
            payload = request.data if isinstance(request.data, dict) else json.loads(request.body.decode())

            project = Project.objects.get(id=pk)

            branch = payload.get("ref", "").split("/")[-1]
            head_commit = payload.get("head_commit")

            if not head_commit:
                return Response(
                    {"status": "ignored", "message": "No head_commit"},
                    status=status.HTTP_200_OK
                )

            message = head_commit.get("message", "")
            commit_id = head_commit.get("id")
            author = head_commit.get("author", {}).get("name")

            updated_items = []
            handled_ids = set()

            # -----------------------------------
            # 1️⃣ Explicit status per task
            # -----------------------------------

            for task_id, keyword in EXPLICIT_TASK_STATUS_REGEX.findall(message):
                task_id = int(task_id)
                new_status = resolve_status(keyword)

                if not new_status or not is_status_allowed(branch, new_status):
                    continue

                try:
                    work_item = WorkItems.objects.get(id=task_id, project=project)
                except WorkItems.DoesNotExist:
                    continue

                if work_item.status != new_status:
                    old_status = work_item.status
                    work_item.status = new_status
                    work_item.save(update_fields=["status", "updated_at"])

                    updated_items.append({
                        "work_item": work_item.id,
                        "from": old_status,
                        "to": new_status,
                        "commit": commit_id,
                        "branch": branch,
                        "author": author,
                    })

                handled_ids.add(task_id)

            # -----------------------------------
            # 2️⃣ Global fallback status
            # -----------------------------------

            global_match = GLOBAL_STATUS_REGEX.search(message)
            if global_match:
                global_status = resolve_status(global_match.group("status"))

                if global_status and is_status_allowed(branch, global_status):
                    all_ids = {int(i) for i in TASK_ID_REGEX.findall(message)}
                    unhandled_ids = all_ids - handled_ids

                    for task_id in unhandled_ids:
                        try:
                            work_item = WorkItems.objects.get(id=task_id, project=project)
                        except WorkItems.DoesNotExist:
                            continue

                        if work_item.status != global_status:
                            old_status = work_item.status
                            work_item.status = global_status
                            work_item.save(update_fields=["status", "updated_at"])

                            updated_items.append({
                                "work_item": work_item.id,
                                "from": old_status,
                                "to": global_status,
                                "commit": commit_id,
                                "branch": branch,
                                "author": author,
                            })

            # -----------------------------------
            # 3️⃣ Store Activity Log
            # -----------------------------------

            activity_log = ProjectActivityLog.objects.create(
                project=project,
                activity={
                    "event_type": "github_push",
                    "branch": branch,
                    "repository": payload.get("repository", {}).get("name"),
                    "pusher": payload.get("pusher", {}).get("name"),
                    "head_commit": head_commit,
                    "updated_work_items": updated_items,
                }
            )

            return Response(
                {
                    "status": "success",
                    "branch": branch,
                    "updated_work_items": updated_items,
                    "activity_log_id": activity_log.id,
                },
                status=status.HTTP_200_OK
            )

        except Project.DoesNotExist:
            return Response(
                {"status": "error", "message": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.exception("Webhook processing failed")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
