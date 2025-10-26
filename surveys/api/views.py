from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from submissions.models import AnswerSet

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

    def _success_response(self, message, code, status_code, data=None):
        return Response(
            {"code": code, "message": message, "data": data or {}},
            status=status_code,
        )

    def _error_response(self, message, code, status_code, errors=None):
        return Response(
            {"code": code, "message": message, "errors": errors or {}},
            status=status_code,
        )

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
            "list_forms_deleted",
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

        return self._success_response(
            code="SUCCESS",
            message=_("نظرسنجی با موفقیت ساخته شد"),
            data={
                "survey_uuid": survey.uuid,
                "form_uuid": survey_form.uuid,
            },
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def soft_delete(self, request, *args, **kwargs):
        try:
            survey = Survey.objects.get(uuid=kwargs["uuid"])

            self.check_object_permissions(request, survey)

            if survey.deleted_at is not None:
                return self._error_response(
                    code="SURVEY_ALREADY_DELETED",
                    message=_("نظرسنجی قبلا حدف شده است"),
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            soft_delete_time = timezone.now()

            with transaction.atomic():
                survey.deleted_at = soft_delete_time
                survey.save(update_fields=["deleted_at"])

                forms = list(survey.forms.filter(deleted_at__isnull=True))

                all_answer_sets = []
                all_answers = []

                for form in forms:
                    form.deleted_at = soft_delete_time
                    answer_sets = list(form.answer_sets.filter(deleted_at__isnull=True))
                    for answer_set in answer_sets:
                        answer_set.deleted_at = soft_delete_time
                        answers = list(
                            answer_set.answers.filter(deleted_at__isnull=True)
                        )
                        for answer in answers:
                            answer.deleted_at = soft_delete_time
                        all_answers.extend(answers)
                    all_answer_sets.extend(answer_sets)

                if all_answers:
                    AnswerSet.answers.field.model.objects.bulk_update(
                        all_answers, ["deleted_at"]
                    )
                if all_answer_sets:
                    form.answer_sets.field.model.objects.bulk_update(
                        all_answer_sets, ["deleted_at"]
                    )
                if forms:
                    survey.forms.field.model.objects.bulk_update(forms, ["deleted_at"])

            return self._success_response(
                code="SUCCESS",
                message=_("نظرسنجی حدف شد."),
                data={},
                status_code=status.HTTP_200_OK,
            )

        except Survey.DoesNotExist:
            return self._error_response(
                code="SURVEY_NOT_EXISTS",
                message=_("نظرسنجی یافت نشد"),
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"])
    def revoke_delete(self, request, *args, **kwargs):
        try:
            survey = Survey.objects.get(uuid=kwargs["uuid"])

            self.check_object_permissions(request, survey)

            if survey.deleted_at is None:
                return self._error_response(
                    code="SURVEY_NOT_DELETED",
                    message=_("نظرسنجی حدف نشده است"),
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            survey_delete_time = survey.deleted_at
            with transaction.atomic():
                survey.deleted_at = None
                survey.save(update_fields=["deleted_at"])

                forms = list(survey.forms.filter(deleted_at=survey_delete_time))

                all_answer_sets = []
                all_answers = []

                for form in forms:
                    form.deleted_at = None
                    answer_sets = list(
                        form.answer_sets.filter(deleted_at=survey_delete_time)
                    )
                    for answer_set in answer_sets:
                        answer_set.deleted_at = None
                        answers = list(
                            answer_set.answers.filter(deleted_at=survey_delete_time)
                        )
                        for answer in answers:
                            answer.deleted_at = None
                        all_answers.extend(answers)
                    all_answer_sets.extend(answer_sets)

                if forms:
                    survey.forms.field.model.objects.bulk_update(forms, ["deleted_at"])
                if all_answer_sets:
                    form.answer_sets.field.model.objects.bulk_update(
                        all_answer_sets, ["deleted_at"]
                    )
                if all_answers:
                    AnswerSet.answers.field.model.objects.bulk_update(
                        all_answers, ["deleted_at"]
                    )

            return self._success_response(
                code="SUCCESS",
                message=_("نظرسنجی بازیابی شد."),
                data={},
                status_code=status.HTTP_200_OK,
            )

        except Survey.DoesNotExist:
            return self._error_response(
                code="SURVEY_NOT_EXISTS",
                message=_("نظرسنجی یافت نشد"),
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["get"], url_path="archived")
    def list_deleted(self, request, *args, **kwargs):
        self.check_permissions(request)

        queryset = Survey.objects.filter(deleted_at__isnull=False)
        if queryset:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        else:
            return self._error_response(
                code="NOT_FOUND",
                message=_("نظرسنجی بایگانی شده ای یافت نشد"),
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["get"], url_path="archived")
    def list_forms_deleted(self, request, *args, **kwargs):
        survey = Survey.objects.get(uuid=kwargs["uuid"])

        self.check_object_permissions(request, survey)

        queryset = SurveyForm.objects.filter(deleted_at__isnull=False, parent=survey)
        if not queryset:
            return self._error_response(
                code="NOT_FOUND",
                message=_("فرم آرشیو شده برای این نظرسنجی وجود ندارد."),
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
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

    def _success_response(self, message, code, status_code, data=None):
        return Response(
            {"code": code, "message": message, "data": data or {}},
            status=status_code,
        )

    def _error_response(self, message, code, status_code, errors=None):
        return Response(
            {"code": code, "message": message, "errors": errors or {}},
            status=status_code,
        )

    def get_permissions(self):
        if self.action in ["create", "list"]:
            return [IsManagementOrProfessorOrAdmin()]
        elif self.action in [
            "retrieve",
            "delete",
            "soft_delete",
            "revoke_delete",
            "activate_form",
        ]:
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
                if parent.active_version:
                    parent.active_version = None
                    parent.save()

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

                return self._success_response(
                    code="SUCCESS",
                    message=_("فرم پرسشنامه بروزرسانی شد."),
                    data={},
                    status_code=status.HTTP_201_CREATED,
                )

            except IntegrityError:
                return self._error_response(
                    code="FORM_VERSION_EXISTS",
                    message=_("فرم پرسشنامه با این شماره وجود دارد."),
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

    @action(detail=True, methods=["post"])
    def soft_delete(self, request, *args, **kwargs):
        try:
            survey_uuid = kwargs["survey_uuid"]
            form_uuid = kwargs["uuid"]

            form = SurveyForm.objects.get(parent__uuid=survey_uuid, uuid=form_uuid)
            self.check_object_permissions(request, form)

            if form.deleted_at is not None:
                return self._error_response(
                    code="FORM_ALREADY_DELETED",
                    message=_("فرم نظرسنجی قبلا حدف شده است"),
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            soft_delete_time = timezone.now()
            settings = form.settings
            survey = form.parent

            with transaction.atomic():

                form.deleted_at = soft_delete_time
                form.save(update_fields=["deleted_at"])

                if settings.is_active:
                    settings.is_active = False
                    settings.save(update_fields=["is_active"])

                    survey.active_version = None
                    survey.save(update_fields=["active_version"])

                answer_sets = list(form.answer_sets.filter(deleted_at__isnull=True))
                all_answers = []

                for answer_set in answer_sets:
                    answer_set.deleted_at = soft_delete_time
                    answers = list(answer_set.answers.filter(deleted_at__isnull=True))
                    for answer in answers:
                        answer.deleted_at = soft_delete_time
                    all_answers.extend(answers)

                if all_answers:
                    AnswerSet.answers.field.model.objects.bulk_update(
                        all_answers, ["deleted_at"]
                    )

                if answer_sets:
                    SurveyForm.answer_sets.field.model.objects.bulk_update(
                        answer_sets, ["deleted_at"]
                    )

            return self._success_response(
                code="SUCCESS",
                message=_("فرم حذف شد."),
                data={},
                status_code=status.HTTP_200_OK,
            )

        except SurveyForm.DoesNotExist:
            return self._error_response(
                code="FORM_DOES_NOT_EXIST",
                message=_("فرم یافت نشد"),
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"])
    def revoke_delete(self, request, *args, **kwargs):
        try:
            survey_uuid = kwargs["survey_uuid"]
            form_uuid = kwargs["uuid"]

            form = SurveyForm.objects.get(parent__uuid=survey_uuid, uuid=form_uuid)
            form_delete_time = form.deleted_at

            self.check_object_permissions(request, form)

            if form_delete_time is None:
                return self._error_response(
                    code="FORM_NOT_DELETED",
                    message=_("فرم نظرسنجی حدف نشده است"),
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                form.deleted_at = None
                form.save(update_fields=["deleted_at"])

                answer_sets = list(form.answer_sets.filter(deleted_at=form_delete_time))
                all_answers = []
                for answer_set in answer_sets:
                    answer_set.deleted_at = None
                    answers = list(
                        answer_set.answers.filter(deleted_at=form_delete_time)
                    )
                    for answer in answers:
                        answer.deleted_at = None
                    all_answers.extend(answers)

                if all_answers:
                    AnswerSet.answers.field.model.objects.bulk_update(
                        all_answers, ["deleted_at"]
                    )

                if answer_sets:
                    SurveyForm.answer_sets.field.model.objects.bulk_update(
                        answer_sets, ["deleted_at"]
                    )
            return self._success_response(
                code="SUCCESS",
                message=_("فرم بازیابی شد."),
                data={},
                status_code=status.HTTP_200_OK,
            )

        except SurveyForm.DoesNotExist:
            return self._error_response(
                code="FORM_DOES_NOT_EXIST",
                message=_("فرم یافت نشد"),
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"], url_path="activate")
    def activate_form(self, request, *args, **kwargs):
        try:
            survey_uuid = kwargs["survey_uuid"]
            form_uuid = kwargs["uuid"]

            form = SurveyForm.objects.get(
                parent__uuid=survey_uuid, uuid=form_uuid, deleted_at__isnull=True
            )
            self.check_object_permissions(request, form)

            settings = form.settings

            if settings.is_active:
                return self._error_response(
                    code="FORM_ALREADY_ACTIVATED",
                    message=_("فرم قبلا فعال شده است."),
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            settings.is_active = True
            settings.save(update_fields=["is_active"])

            return self._success_response(
                code="SUCCESS",
                message=_("فرم فعال شد"),
                data={},
                status_code=status.HTTP_200_OK,
            )
        except SurveyForm.DoesNotExist:
            return self._error_response(
                code="FORM_DOES_NOT_EXIST",
                message=_("فرم یافت نشد"),
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )


class SurveyFormSettingsViewSet(UpdateModelMixin, RetrieveModelMixin, GenericViewSet):
    serializer_class = SurveyFormSettingsSerializer
    queryset = SurveyFormSettings.objects.all()
    http_method_names = ["get", "patch"]
    permission_classes = [IsOwnerOrAdmin]
