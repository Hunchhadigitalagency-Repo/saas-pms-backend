from rest_framework.permissions import BasePermission, SAFE_METHODS
from customer.models import ActiveClient, UserClientRole


class ProjectAccessPermission(BasePermission):
    """
    Client role-based + object-level permission.

    - owner: full access to all projects in the active client/tenant
    - member: read/write only if assigned to the project
    - viewer: read-only only if assigned to the project
    - no active client or no role: deny
    """

    def has_permission(self, request, view):
        """
        Runs for *all* requests, including list/create.
        Denies early if user has no active client or no role in that client.
        """
        user = getattr(request, "user", None)
        if not user or user.is_anonymous:
            return False

        active = ActiveClient.objects.select_related("client").filter(user=user).first()
        if not active:
            return False

        role = (
            UserClientRole.objects.filter(user=user, client=active.client)
            .values_list("role", flat=True)
            .first()
        )
        return bool(role)

    def has_object_permission(self, request, view, obj):
        """
        Runs for retrieve/update/partial_update/destroy and any detail=True actions
        that call self.get_object().
        """
        user = getattr(request, "user", None)
        if not user or user.is_anonymous:
            return False

        active = ActiveClient.objects.select_related("client").filter(user=user).first()
        if not active:
            return False

        role = (
            UserClientRole.objects.filter(user=user, client=active.client)
            .values_list("role", flat=True)
            .first()
        )
        if not role:
            return False

        if role == "owner":
            return True

        # Must be assigned to access at all for member/viewer
        is_assigned = obj.projectmembers_set.filter(user=user).exists()

        # Read-only methods
        if request.method in SAFE_METHODS:
            return is_assigned

        # Write methods allowed only for client-role member + assigned
        return role == "member" and is_assigned
