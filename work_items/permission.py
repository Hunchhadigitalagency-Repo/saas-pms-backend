from django.db.models import Q
from rest_framework.permissions import BasePermission, SAFE_METHODS
from customer.models import ActiveClient, UserClientRole


class WorkItemAccessPermission(BasePermission):
    """
    Client role + object permission for WorkItems.

    owner: full access
    member: access if (assigned_to) OR (project membership)
    viewer: read-only if (assigned_to) OR (project membership)
    """

    def _get_role(self, user):
        active = ActiveClient.objects.select_related("client").filter(user=user).first()
        if not active:
            return None, None

        role = (
            UserClientRole.objects
            .filter(user=user, client=active.client)
            .values_list("role", flat=True)
            .first()
        )
        return active, role

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or user.is_anonymous:
            return False

        _, role = self._get_role(user)
        return bool(role)

    def has_object_permission(self, request, view, obj):
        user = request.user
        active, role = self._get_role(user)
        if not active or not role:
            return False

        if role == "owner":
            return True

        # Conditions: assigned directly OR belongs to project team
        is_assigned = obj.assigned_to.filter(id=user.id).exists()
        in_project = False
        if obj.project_id:
            in_project = obj.project.projectmembers_set.filter(user=user).exists()

        allowed = is_assigned or in_project

        if request.method in SAFE_METHODS:
            return allowed

        # write only for member (not viewer) and must be allowed
        return role == "member" and allowed
