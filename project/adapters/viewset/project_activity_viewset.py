import re
from work_items.models import WorkItems
from project.models import Project, ProjectActivityLog
from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework import status
from project.adapters.serializers.project_activity_log_serializer import ProjectActivityLogSerializer
from utils.custom_paginator import CustomPaginator
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from pms.jwt_auth import CookieJWTAuthentication
import json
import logging

logger = logging.getLogger(__name__)

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
        print(f"🔵 Webhook received for project ID: {pk}")
        try:
            payload = request.data if isinstance(request.data, dict) else json.loads(request.body.decode())
            print(f"📦 Payload parsed successfully. Repository: {payload.get('repository', {}).get('name')}")

            # Get project
            try:
                project = Project.objects.get(id=pk)
                print(f"✅ Project found: {project.name} (ID: {project.id})")
            except Project.DoesNotExist:
                print(f"❌ Project not found with ID: {pk}")
                return Response(
                    {"status": "error", "message": "Project not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            branch = payload.get("ref", "").split("/")[-1]
            commits = payload.get("commits", [])
            print(f"🌿 Branch: {branch}, Total commits: {len(commits)}")

            if not commits:
                print(f"⚠️ No commits in push for project {project.name}")
                return Response(
                    {"status": "ignored", "message": "No commits in push"},
                    status=status.HTTP_200_OK
                )

            updated_items = []
            for idx, commit in enumerate(commits, 1):
                message = commit.get("message", "")
                commit_id = commit.get("id")
                author = commit.get("author", {}).get("name")
                print(f"📝 Processing commit {idx}/{len(commits)}: {commit_id[:7]} by {author}")
                print(f"   Message: {message}")

                handled_ids = set()

                # 1️⃣ Explicit per-task statuses (TASK-12:#done)
                explicit_matches = EXPLICIT_TASK_STATUS_REGEX.findall(message)
                if explicit_matches:
                    print(f"   🔍 Found {len(explicit_matches)} explicit task status(es)")
                
                for task_id, keyword in explicit_matches:
                    task_id = int(task_id)
                    new_status = resolve_status(keyword)
                    print(f"      Task {task_id}: keyword '{keyword}' -> status '{new_status}'")

                    if not new_status or not is_status_allowed(branch, new_status):
                        print(f"      ⏭️ Task {task_id} skipped: status '{new_status}' not allowed for branch '{branch}'")
                        continue

                    try:
                        work_item = WorkItems.objects.get(id=task_id, project=project)
                        print(f"      ✅ Work item {task_id} found")
                    except WorkItems.DoesNotExist:
                        print(f"      ❌ Work item {task_id} not found in project {project.name}")
                        continue

                    if work_item.status != new_status:
                        old_status = work_item.status
                        work_item.status = new_status
                        work_item.save(update_fields=["status", "updated_at"])
                        print(f"      ✏️ Task {task_id} updated: {old_status} → {new_status}")

                        updated_items.append({
                            "work_item": work_item.id,
                            "from": old_status,
                            "to": new_status,
                            "commit": commit_id,
                            "branch": branch,
                            "author": author,
                        })
                    else:
                        print(f"      ℹ️ Task {task_id} already has status '{new_status}'")

                    handled_ids.add(task_id)

                # 2️⃣ Global status fallback (TASK-1 TASK-2 #done)
                global_match = GLOBAL_STATUS_REGEX.search(message)
                if global_match:
                    global_keyword = global_match.group("status")
                    global_status = resolve_status(global_keyword)
                    print(f"   🌐 Found global status: '{global_keyword}' -> '{global_status}'")

                    if global_status and is_status_allowed(branch, global_status):
                        all_ids = {int(i) for i in TASK_ID_REGEX.findall(message)}
                        unhandled_ids = all_ids - handled_ids
                        print(f"   🔢 Found {len(all_ids)} task ID(s), {len(unhandled_ids)} unhandled")

                        for task_id in unhandled_ids:
                            try:
                                work_item = WorkItems.objects.get(id=task_id, project=project)
                                print(f"      ✅ Work item {task_id} found")
                            except WorkItems.DoesNotExist:
                                print(f"      ❌ Work item {task_id} not found in project {project.name}")
                                continue

                            if work_item.status != global_status:
                                old_status = work_item.status
                                work_item.status = global_status
                                work_item.save(update_fields=["status", "updated_at"])
                                print(f"      ✏️ Task {task_id} updated (global): {old_status} → {global_status}")

                                updated_items.append({
                                    "work_item": work_item.id,
                                    "from": old_status,
                                    "to": global_status,
                                    "commit": commit_id,
                                    "branch": branch,
                                    "author": author,
                                })
                            else:
                                print(f"      ℹ️ Task {task_id} already has status '{global_status}'")
                    else:
                        print(f"      ⏭️ Global status '{global_status}' not allowed for branch '{branch}'")
                else:
                    print(f"   ℹ️ No global status found in commit message")

            print(f"📊 Total work items updated: {len(updated_items)}")

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
            print(f"💾 Activity log created (ID: {activity_log.id})")

            print(f"✅ Webhook processing completed successfully for project {project.name}")
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

        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {str(e)}")
            return Response(
                {"status": "error", "message": "Invalid JSON payload"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            print(f"❌ Webhook processing failed: {str(e)}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )