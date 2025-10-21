from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
                request.user.is_authenticated and
                request.user == obj.user)

class NotAllowed(BasePermission):
    def has_permission(self, request, view):
        return False


class IsSurveyOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True

        if hasattr(obj, "survey_form"):
            if hasattr(obj.survey_form, "parent"):
                if hasattr(obj.survey_form.parent, "created_by"):
                    return request.user == obj.survey_form.parent.created_by

        return False