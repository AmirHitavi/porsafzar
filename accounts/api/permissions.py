from rest_framework.permissions import BasePermission


class IsNotAuthenticated(BasePermission):
    """
    Only allow access if the user is NOT authenticated.
    """

    def has_permission(self, request, view):
        return not request.user or not request.user.is_authenticated


class IsStaffOrSuperUser(BasePermission):
    """
    Allows access only to staff or admin users.
    """

    def has_permission(self, request, view):
        return bool(
            request.user and (request.user.is_staff or request.user.is_superuser)
        )
