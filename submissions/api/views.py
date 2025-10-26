from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from surveys.models import Survey

from ..models import AnswerSet
from .permissions import IsOwner, IsSurveyOwnerOrAdmin, NotAllowed
from .serializers import AnswerSetSerializer
from .services import create_answer, create_answerset


class AnswerSetViewSet(ModelViewSet):
    serializer_class = AnswerSetSerializer
    http_method_names = ["get", "options", "head", "post", "put", "delete"]
    lookup_field = "uuid"

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

    def get_active_survey_form(self):
        survey_uuid = self.kwargs.get("survey_uuid")
        try:
            survey = Survey.objects.get(uuid=survey_uuid)
            return survey.active_version
        except Survey.DoesNotExist:
            return None

    def get_queryset(self):
        active_version = self.get_active_survey_form()
        if not active_version:
            return AnswerSet.objects.none()
        return AnswerSet.objects.filter(
            survey_form=active_version, deleted_at__isnull=True
        )

    def get_permissions(self, *args, **kwargs):
        active_form = self.get_active_survey_form()

        if self.action == "create":
            if active_form:
                max_responses_allowed = active_form.settings.max_submissions_per_user
                if max_responses_allowed:
                    return [IsAuthenticated()]
                else:
                    return [AllowAny()]
            else:
                return [AllowAny()]

        elif self.action == "update":
            if active_form:
                is_editable = active_form.settings.is_editable
                if is_editable:
                    return [IsOwner()]

            return [NotAllowed()]

        else:
            return [IsSurveyOwnerOrAdmin()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    def create(self, request, *args, **kwargs):

        active_form = self.get_active_survey_form()

        if active_form is None:
            return self._error_response(
                code="FORM_NOT_FOUND",
                message=_("پرسشنامه معتبری یافت نشد."),
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        settings = active_form.settings

        if settings.is_active is False:
            return self._error_response(
                code="FORM_NOT_ACTIVE",
                message=_("پرسشنامه غیر فعال است و امکان ثبت جواب وجود ندارد"),
                errors={},
                status_code=status.HTTP_403_FORBIDDEN,
            )

        max_responses_allowed = settings.max_submissions_per_user
        user = request.user if request.user.is_authenticated else None

        if max_responses_allowed and user:
            user_submissions = AnswerSet.objects.filter(
                survey_form=active_form,
                user=user,
            ).count()

            if user_submissions >= max_responses_allowed:
                return self._error_response(
                    code="TOO_MANY_SUBMISSIONS",
                    message=_(
                        f"شما نمی توانید بیش از {max_responses_allowed} پاسخ ارسال کنید."
                    ),
                    errors={},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        metadata = serializer.validated_data.get("metadata")

        with transaction.atomic():
            answer_set = create_answerset(
                user=user,
                survey_form=active_form,
                metadata=metadata,
            )

            for question_name, answer_value in metadata.items():
                create_answer(
                    answer_set=answer_set,
                    question_name=question_name,
                    answer_value=answer_value,
                )

        return self._success_response(
            code="SUCCESS",
            message=_("نظر شما ثبت شد"),
            data={
                "answer_set": answer_set.uuid,
                "survey_form": active_form.uuid,
                "user": user.phone_number if user else None,
            },
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):

        active_form = self.get_active_survey_form()

        if not active_form:
            return Response(
                {"detail": _("پرسش‌نامه معتبر یافت نشد.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not active_form.settings.is_active:
            return Response(
                {"detail": _("پرسشنامه غیر فعال است و امکان ثبت جواب وجود ندارد")},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:

            with transaction.atomic():

                answer_set = self.get_object()
                answer_set.answers.all().delete()

                serializer = self.get_serializer(answer_set, data=request.data)
                serializer.is_valid(raise_exception=True)
                metadata = serializer.validated_data.get("metadata")
                answer_set = serializer.save()

                for question_name, answer_value in metadata.items():
                    create_answer(
                        answer_set=answer_set,
                        question_name=question_name,
                        answer_value=answer_value,
                    )

            return Response(
                {"message": _("نظر شما بروزرسانی شد")},
                status=status.HTTP_201_CREATED,
            )
        except AnswerSet.DoesNotExist:
            return Response(
                {"message": _("چنین جوابی وجود ندارد.")}, status=status.HTTP_201_CREATED
            )

    @action(detail=True, methods=["post"])
    def soft_delete(self, request, *args, **kwargs):
        try:
            answerset = self.get_object()

            soft_delete_time = timezone.now()

            with transaction.atomic():
                answerset.deleted_at = soft_delete_time
                answerset.save(update_fields=["deleted_at"])

                # bulk_update
                answers = list(answerset.answers.filter(deleted_at__isnull=True))
                for answer in answers:
                    answer.deleted_at = soft_delete_time

                AnswerSet.answers.field.model.objects.bulk_update(
                    answers, ["deleted_at"]
                )

            return Response(
                {"detail": _("جواب پرسش نامه حدف شد.")}, status=status.HTTP_200_OK
            )
        except AnswerSet.DoesNotExist:
            return Response(
                {"detail": _("جوابی یافت نشد")}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def revoke_delete(self, request, *args, **kwargs):
        try:
            answerset = AnswerSet.objects.get(uuid=kwargs["uuid"])

            answerset_delete_time = answerset.deleted_at

            with transaction.atomic():

                answerset.deleted_at = None
                answerset.save()

                answers = list(
                    answerset.answers.filter(deleted_at=answerset_delete_time)
                )

                for answer in answers:
                    answer.deleted_at = None

                AnswerSet.answers.field.model.objects.bulk_update(
                    answers, ["deleted_at"]
                )

            return Response(
                {"detail": _("جواب پرسش نامه بازیابی شد.")},
                status=status.HTTP_200_OK,
            )
        except AnswerSet.DoesNotExist:
            return Response(
                {"detail": _("جوابی یافت نشد")}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["get"], url_path="archived")
    def list_deleted(self, request, *args, **kwargs):
        active_form = self.get_active_survey_form()
        if not active_form:
            return Response(
                {"detail": _("فرم فعال یافت نشد.")}, status=status.HTTP_404_NOT_FOUND
            )

        queryset = AnswerSet.objects.filter(
            deleted_at__isnull=False,
            survey_form=active_form,
        )

        if not queryset:
            return Response(
                {"detail": _("جواب بایگانی شده ای وجود ندارد.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
