from rest_framework.permissions import BasePermission

from surveys.models import Survey


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated
            and hasattr(obj, "user")
            and obj.user == request.user
        )


class IsSurveyOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_staff or request.user.is_superuser:
            return True

        survey_uuid = view.kwargs.get("survey_uuid")
        if not survey_uuid:
            return False

        survey = Survey.objects.filter(uuid=survey_uuid).first()
        if not survey:
            return False

        return survey.created_by == request.user


    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True

        if hasattr(obj, "survey_form"):
            if hasattr(obj.survey_form, "parent"):
                if hasattr(obj.survey_form.parent, "created_by"):
                    return request.user == obj.survey_form.parent.created_by

        return False


class IsOwnerOrSurveyOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        is_owner = IsOwner().has_object_permission(request, view, obj)
        is_survey_admin = IsSurveyOwnerOrAdmin().has_object_permission(
            request, view, obj
        )
        return is_owner or is_survey_admin
