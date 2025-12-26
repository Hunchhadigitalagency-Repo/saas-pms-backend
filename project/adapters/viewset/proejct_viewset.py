from backend.work_items.models import WorkItems
from project.permission import ProjectAccessPermission
from customer.models import ActiveClient, UserClientRole
from project.models import Project, ProjectActivityLog
from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from project.adapters.serializers.project_serializer import ProjectSerializer, OnGoingProjectSerializer, ProjectWriteSerializer
from project.adapters.serializers.project_activity_log_serializer import ProjectActivityLogSerializer
from utils.custom_paginator import CustomPaginator
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from pms.jwt_auth import CookieJWTAuthentication
import json
import logging

logger = logging.getLogger(__name__)

class ProjectViewSet(viewsets.ModelViewSet):
    """
    Projects API with:
    - cookie JWT auth
    - list filtering/search/ordering
    - role-based scoping in get_queryset()
    - object-level permissions via ProjectAccessPermission
    - read/write serializer switching
    """
    serializer_class = ProjectSerializer
    pagination_class = CustomPaginator
    permission_classes = [IsAuthenticated, ProjectAccessPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "priority"]
    search_fields = ["name", "description"]
    ordering_fields = ["due_date", "created_at", "priority"]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        user = self.request.user

        active = ActiveClient.objects.select_related("client").filter(user=user).first()
        if not active:
            return Project.objects.none()

        role = (
            UserClientRole.objects.filter(user=user, client=active.client)
            .values_list("role", flat=True)
            .first()
        )

        # No role => no access
        if not role:
            return Project.objects.none()

        qs = Project.objects.all()

        if role in ("member", "viewer"):
            qs = qs.filter(projectmembers__user=user)

        # Performance (optional but recommended if you return team_members frequently)
        qs = qs.prefetch_related(
            "projectmembers_set__user",
            "projectmembers_set__user__profile",  # adjust if your related_name differs
        )

        return qs.distinct().order_by("-id")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProjectWriteSerializer
        return ProjectSerializer

    def create(self, request, *args, **kwargs):
        # Use write serializer for validation and saving
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        
        # Use read serializer for response to include team_members and all fields
        read_serializer = ProjectSerializer(instance)
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Use write serializer for validation and saving
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        
        # Use read serializer for response to include team_members and all fields
        read_serializer = ProjectSerializer(instance)
        return Response(read_serializer.data)

class OngoingProjectViewSet(viewsets.ModelViewSet):
    """
    Ongoing projects (status='active') with role-based scoping.
    Mirrors `ProjectViewSet` access rules so member/viewer roles only see assigned projects.
    """
    serializer_class = OnGoingProjectSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated, ProjectAccessPermission]
    authentication_classes = [CookieJWTAuthentication]

    def get_queryset(self):
        user = self.request.user

        active = ActiveClient.objects.select_related("client").filter(user=user).first()
        if not active:
            return Project.objects.none()

        role = (
            UserClientRole.objects.filter(user=user, client=active.client)
            .values_list("role", flat=True)
            .first()
        )

        if not role:
            return Project.objects.none()

        qs = Project.objects.filter(status="active")

        if role in ("member", "viewer"):
            qs = qs.filter(projectmembers__user=user)

        qs = qs.prefetch_related(
            "projectmembers_set__user",
            "projectmembers_set__user__profile",
        )

        return qs.distinct().order_by("-id")

import re

# TASK-12:#done | BUG-7:#inprogress
EXPLICIT_TASK_STATUS_REGEX = re.compile(
    r'\b[A-Z]+-(?P<id>\d+)\s*:\s*#(?P<status>[a-zA-Z_]+)\b',
    re.IGNORECASE
)

# TASK-12 BUG-7 WI-9
TASK_ID_REGEX = re.compile(
    r'\b[A-Z]+-(?P<id>\d+)\b',
    re.IGNORECASE
)

# #done #start #inprogress
GLOBAL_STATUS_REGEX = re.compile(
    r'#(?P<status>pending|start|inprogress|done|complete|closed)',
    re.IGNORECASE
)


STATUS_MAP = {
    "pending": "pending",
    "start": "in_progress",
    "inprogress": "in_progress",
    "done": "completed",
    "complete": "completed",
    "closed": "completed",
}


def resolve_status(keyword: str):
    return STATUS_MAP.get(keyword.lower())


def is_status_allowed(branch: str, status: str) -> bool:
    if branch.startswith("feature"):
        return status in ["pending", "in_progress"]
    if branch in ["development", "dev"]:
        return status in ["in_progress"]
    if branch in ["main", "master", "production"]:
        return status == "completed"
    return True  # fallback


class ProjectActivityLogViewSet(viewsets.ModelViewSet):
    """
    Project Activity Log API 
    Supports:
    - List all activity logs
    - Retrieve activity logs by project ID via /by-project/{project_id}/
    - GitHub webhook endpoint for push events
    """
    serializer_class = ProjectActivityLogSerializer
    pagination_class = CustomPaginator
    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]
    
    def get_queryset(self):
        return ProjectActivityLog.objects.all().order_by('-created_at')
    
    @action(detail=False, methods=['get'], url_path='by-project/(?P<project_id>[^/.]+)')
    def get_activity_by_project_id(self, request, project_id=None):
        """
        Get activity logs for a specific project.
        URL: /api/v1/project-activity-logs/by-project/{project_id}/
        """
        queryset = ProjectActivityLog.objects.filter(project__id=project_id).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='post-push-event',
        permission_classes=[AllowAny],
        authentication_classes=[]
    )
    def post_push_event(self, request, pk=None):
        try:
            payload = request.data if isinstance(request.data, dict) else json.loads(request.body.decode())

            # Get project
            try:
                project = Project.objects.get(id=pk)
            except Project.DoesNotExist:
                return Response(
                    {"status": "error", "message": "Project not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            branch = payload.get("ref", "").split("/")[-1]
            commits = payload.get("commits", [])

            if not commits:
                return Response(
                    {"status": "ignored", "message": "No commits in push"},
                    status=status.HTTP_200_OK
                )

            updated_items = []

            for commit in commits:
                message = commit.get("message", "")
                commit_id = commit.get("id")
                author = commit.get("author", {}).get("name")

                handled_ids = set()

                # 1️⃣ Explicit per-task statuses (TASK-12:#done)
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

                # 2️⃣ Global status fallback (TASK-1 TASK-2 #done)
                global_match = GLOBAL_STATUS_REGEX.search(message)
                if global_match:
                    global_status = resolve_status(global_match.group("status"))

                    if global_status and is_status_allowed(branch, global_status):
                        all_ids = {int(i) for i in TASK_ID_REGEX.findall(message)}

                        for task_id in all_ids - handled_ids:
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

            # 3️⃣ Store activity log (unchanged behavior)
            activity_log = ProjectActivityLog.objects.create(
                project=project,
                activity={
                    "event_type": "github_push",
                    "branch": branch,
                    "repository": payload.get("repository", {}).get("name"),
                    "pusher": payload.get("pusher", {}).get("name"),
                    "commits": commits,
                    "updated_work_items": updated_items,
                }
            )

            return Response(
                {
                    "status": "success",
                    "project": project.name,
                    "branch": branch,
                    "updated_work_items": updated_items,
                    "activity_log_id": activity_log.id,
                },
                status=status.HTTP_200_OK
            )

        except json.JSONDecodeError:
            return Response(
                {"status": "error", "message": "Invalid JSON payload"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.exception("Webhook processing failed")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )