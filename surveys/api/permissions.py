from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.permissions import BasePermission

User = get_user_model()


class IsManagementOrProfessorOrAdmin(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if user.is_staff or user.is_superuser:
            return True

        if user and user.is_authenticated:
            if user.role in [
                User.UserRole.MANAGEMENT.value,
                User.UserRole.PROFESSOR.value,
            ]:
                return True

        return False


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):

        return bool(
            request.user == obj.created_by
            or request.user.is_staff
            or request.user.is_superuser
        )
