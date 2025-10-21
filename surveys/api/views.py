from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Survey, SurveyForm, SurveyFormSettings
from .permissions import IsManagementOrProfessorOrAdmin, IsOwnerOrAdmin
from .serializers import (
    CreateSurveySerializer,
    SurveyFormSerializer,
    SurveyFormSettingsSerializer,
    SurveySerializer,
)
from .services import create_questions, create_survey, create_survey_form


class SurveyViewSet(ModelViewSet):

    queryset = Survey.objects.filter(deleted_at__isnull=True)
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateSurveySerializer
        return SurveySerializer

    def get_permissions(self):

        if self.action in [
            "retrieve",
            "partial_update",
            "destroy",
            "soft_delete",
            "revoke_delete",
            "list_deleted",
            "list_forms_deleted",
        ]:
            return [IsOwnerOrAdmin()]

        if self.action in ["create"]:
            return [IsManagementOrProfessorOrAdmin()]

        return [IsAuthenticated()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        json_data = serializer.validated_data.get("data")

        with transaction.atomic():
            # create a survey
            survey_title = json_data.get("title")
            survey = create_survey(self.request.user, survey_title)

            # create a survey form
            survey_form = create_survey_form(
                parent=survey, json_data=json_data, version=1
            )

            # create questions
            pages = json_data.get("pages")
            create_questions(form=survey_form, pages=pages)

        return Response(
            {"detail": _("نظرسنجی با موفقیت ساخته شد")}, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def soft_delete(self, request, *args, **kwargs):
        try:
            survey = self.get_object()

            with transaction.atomic():
                soft_delete_time = timezone.now()
                survey.deleted_at = soft_delete_time
                survey.save()

                forms = survey.forms.all()
                for form in forms:
                    form.deleted_at = soft_delete_time
                    form.save()

                return Response(
                    {"detail": _("نظرسنجی حدف شد.")}, status=status.HTTP_200_OK
                )

        except Survey.DoesNotExist:
            return Response(
                {"detail": _("نظرسنجی یافت نشد")}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def revoke_delete(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                survey = Survey.objects.get(
                    uuid=kwargs["uuid"], deleted_at__isnull=False
                )
                survey.deleted_at = None
                survey.save()

                forms = survey.forms.all()
                for form in forms:
                    form.deleted_at = None
                    form.save()

                return Response(
                    {"detail": _("نظرسنجی بایگانی شد.")}, status=status.HTTP_200_OK
                )
        except Survey.DoesNotExist:
            return Response(
                {"detail": _("نظرسنجی یافت نشد")}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["get"], url_path="archived")
    def list_deleted(self, request, *args, **kwargs):
        queryset = Survey.objects.filter(deleted_at__isnull=False)
        if queryset:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        else:
            return Response(
                {"detail": _("نظرسنجی بایگانی شده ای یافت نشد")},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["get"], url_path="archived")
    def list_forms_deleted(self, request, *args, **kwargs):
        queryset = SurveyForm.objects.filter(
            deleted_at__isnull=False, parent__uuid=self.kwargs["uuid"]
        )
        if not queryset:
            return Response(
                {"detail": _("فرم آرشیو شده برای این نظرسنجی وجود ندارد.")},
                status=status.HTTP_404_NOT_FOUND,
            )
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SurveyFormSerializer(queryset, many=True)
        return Response(serializer.data)


class SurveyFormViewSet(ModelViewSet):
    serializer_class = SurveyFormSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "options", "head", "post", "delete"]

    def get_permissions(self):
        if self.action in ["create"]:
            return [IsManagementOrProfessorOrAdmin()]
        elif self.action in ["delete", "soft_delete", "revoke_delete"]:
            return [IsOwnerOrAdmin()]
        else:
            return [IsAuthenticated()]

    def get_queryset(self):
        return SurveyForm.objects.filter(
            deleted_at__isnull=True, parent__uuid=self.kwargs["survey_uuid"]
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    # use for update a survey
    def create(self, request, *args, **kwargs):

        parent = Survey.objects.get(uuid=self.kwargs["survey_uuid"])

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        version = serializer.validated_data["version"]
        description = serializer.validated_data["description"]
        metadata = serializer.validated_data["metadata"]

        with transaction.atomic():
            # update survey parent if it has title in metadata
            parent_title = metadata.get("title", None)
            if parent_title:
                parent.title = parent_title
                parent.save()

            try:
                # create a new survey form
                survey_form = create_survey_form(
                    parent=parent,
                    json_data=metadata,
                    version=version,
                    description=description,
                )
                # create questions
                pages = metadata.get("pages")
                create_questions(form=survey_form, pages=pages)
                return Response(
                    {"detail": _("فرم پرسشنامه بروزرسانی شد.")},
                    status=status.HTTP_201_CREATED,
                )

            except IntegrityError:
                return Response(
                    {"detail": _("فرم پرسشنامه با این شماره وجود دارد.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    @action(detail=True, methods=["post"])
    def soft_delete(self, request, *args, **kwargs):
        try:
            form = self.get_object()

            form.deleted_at = timezone.now()
            form.save()
            return Response({"detail": _("فرم حدف شد.")}, status=status.HTTP_200_OK)

        except SurveyForm.DoesNotExist:
            return Response(
                {"detail": _("فرم یافت نشد")}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def revoke_delete(self, request, *args, **kwargs):
        try:
            form = SurveyForm.objects.get(uuid=kwargs["uuid"], deleted_at__isnull=False)
            form.deleted_at = None
            form.save()
            return Response({"detail": _("فرم بازیابی شد.")}, status=status.HTTP_200_OK)
        except SurveyForm.DoesNotExist:
            return Response(
                {"detail": _("فرم یافت نشد")}, status=status.HTTP_404_NOT_FOUND
            )


class SurveyFormSettings(UpdateModelMixin, RetrieveModelMixin, GenericViewSet):
    serializer_class = SurveyFormSettingsSerializer
    queryset = SurveyFormSettings.objects.all()
    http_method_names = ["get", "patch"]
    permission_classes = [IsOwnerOrAdmin]
