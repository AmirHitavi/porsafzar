from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from . import selectors, services
from .permissions import IsManagementOrProfessorOrAdmin, IsOwnerOrAdmin
from .serializers import (
    SurveyFormSerializer,
    SurveyFormSettingsSerializer,
    SurveySerializer,
    TargetAudienceSerializer,
)


class SurveyViewSet(ModelViewSet):
    serializer_class = SurveySerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        if self.action in ["restore", "list_deleted"]:
            base_queryset = selectors.get_deleted_surveys()
            forms_queryset = selectors.get_all_deleted_survey_forms()
            prefetch_attr = "prefetched_deleted_forms"
        else:
            base_queryset = selectors.get_active_surveys()
            forms_queryset = selectors.get_all_active_survey_forms()
            prefetch_attr = "prefetched_active_forms"

        return base_queryset.select_related(
            "created_by", "active_version"
        ).prefetch_related(
            Prefetch(
                "forms",
                queryset=forms_queryset,
                to_attr=prefetch_attr,
            )
        )

    def get_permissions(self):

        if self.action in [
            "retrieve",
            "partial_update",
            "destroy",
            "restore",
        ]:
            return [IsOwnerOrAdmin()]

        if self.action in [
            "create",
            "list_deleted",
        ]:
            return [IsManagementOrProfessorOrAdmin()]

        return [IsAuthenticated()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data = {"message": _("نظرسنجی با موفقیت ساخته شد")}
        return response

    def destroy(self, request, *args, **kwargs):
        user = request.user
        survey_uuid = kwargs["uuid"]

        if user.is_superuser or user.is_staff:
            survey = selectors.get_survey_by_uuid(survey_uuid)
        else:
            survey = self.get_object()

        self.check_object_permissions(request, survey)
        services.delete_survey(survey=survey, user=user)

        return Response(
            {"message": _("نظرسنجی حدف شده است.")}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def restore(self, request, *args, **kwargs):
        survey = selectors.get_soft_deleted_survey_by_uuid(uuid=self.kwargs.get("uuid"))
        self.check_object_permissions(request, survey)
        services.restore_survey(survey)
        return Response(
            {"message": _("نظرسنجی بازیابی شد.")}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="archived")
    def list_deleted(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SurveyFormViewSet(ModelViewSet):
    serializer_class = SurveyFormSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "options", "head", "post", "delete"]

    def get_permissions(self):
        if self.action in ["create", "list", "list_forms_deleted"]:
            return [IsManagementOrProfessorOrAdmin()]
        elif self.action in [
            "retrieve",
            "destroy",
            "restore",
            "activate_form",
        ]:
            return [IsOwnerOrAdmin()]
        else:
            return [IsAuthenticated()]

    def get_queryset(self):
        if self.action in ["restore", "list_forms_deleted"]:
            base_queryset = selectors.get_all_deleted_forms()
        else:
            base_queryset = selectors.get_all_active_forms()

        return base_queryset.filter(parent__uuid=self.kwargs["survey_uuid"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    # use for update a survey
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"survey_uuid": self.kwargs["survey_uuid"]}
        )
        serializer.is_valid(raise_exception=True)
        survey_form = serializer.save()
        return Response(
            {
                "message": _("فرم پرسشنامه بروزرسانی شد."),
                "data": {
                    "form_uuid": survey_form.uuid,
                },
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if user.is_superuser or user.is_staff:
            form = selectors.get_form_by_uuid(
                parent_uuid=kwargs["survey_uuid"], form_uuid=kwargs["uuid"]
            )
        else:
            form = self.get_object()
        self.check_object_permissions(request, form)
        services.delete_form(form, user)
        return Response({"message": _("فرم حدف شد.")}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def restore(self, request, *args, **kwargs):
        survey_uuid = self.kwargs["survey_uuid"]
        form_uuid = self.kwargs["uuid"]

        form = selectors.get_soft_deleted_form_by_uuid(
            parent_uuid=survey_uuid, form_uuid=form_uuid
        )
        self.check_object_permissions(request, form)
        services.restore_form(form)
        return Response({"message": _("فرم بازیابی شد.")}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate_form(self, request, *args, **kwargs):
        form = self.get_object()
        services.activate_form(form)
        return Response({"message": _("فرم فعال شد")}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="archived")
    def list_forms_deleted(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(parent__uuid=self.kwargs["survey_uuid"])
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SurveyFormSettingsViewSet(UpdateModelMixin, RetrieveModelMixin, GenericViewSet):
    serializer_class = SurveyFormSettingsSerializer
    queryset = selectors.get_all_settings()
    http_method_names = ["get", "patch"]
    permission_classes = [IsOwnerOrAdmin]


class TargetAudienceViewSet(ModelViewSet):
    queryset = selectors.get_all_target_audiences()
    serializer_class = TargetAudienceSerializer
    http_method_names = ["get", "patch", "head", "post", "delete"]
    permission_classes = [IsManagementOrProfessorOrAdmin]
