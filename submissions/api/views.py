from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from surveys.models import Survey

from ..models import AnswerSet
from .serializers import AnswerSetSerializer
from .services import create_answer, create_answerset
from .permissions import IsOwner, NotAllowed, IsSurveyOwnerOrAdmin

#TODO: add field in AnswerSet model to track down number of submissions
class AnswerSetViewSet(ModelViewSet):
    lookup_field = "uuid"
    serializer_class = AnswerSetSerializer
    http_method_names = ["get", "options", "head", "post", "put", "delete"]

    def get_queryset(self):
        try:
            survey = Survey.objects.get(uuid=self.kwargs["survey_uuid"])
            active_version = survey.active_version
            if active_version:
                return AnswerSet.objects.filter(survey_form=active_version, deleted_at__isnull=True)
            else:
                return None
        except Survey.DoesNotExist:
            return None

    def get_permissions(self, *args, **kwargs):
        if self.action == "create":
            survey = Survey.objects.get(uuid=self.kwargs.get("survey_uuid"))
            active_form = survey.active_version

            max_responses_per_user_allowed = active_form.settings.max_submissions_per_user

            if max_responses_per_user_allowed:
                return [IsAuthenticated()]
            else:
                return [AllowAny()]

        elif self.action == "update":
            survey = Survey.objects.get(uuid=self.kwargs.get("survey_uuid"))
            active_form = survey.active_version

            max_responses_per_user_allowed = active_form.settings.max_submissions_per_user

            if max_responses_per_user_allowed:
                return [IsOwner()]
            else:
                return [NotAllowed()]

        else:
            return [IsSurveyOwnerOrAdmin()]

        return super().get_permissions(*args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    def create(self, request, *args, **kwargs):

        active_version = Survey.objects.get(uuid=kwargs["survey_uuid"]).active_version
        max_responses_allowed = active_version.settings.max_submissions_per_user
        user = request.user if request.user.is_authenticated else None

        if max_responses_allowed and user:
            user_submissions = AnswerSet.objects.filter(
                survey_form=active_version,
                user=user,
            ).count()

            if user_submissions >= max_responses_allowed:
                return Response(
                    {"detail": _(f"شما نمی توانید بیش از {max_responses_allowed} پاسخ ارسال کنید.")},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        metadata = serializer.validated_data.get("metadata")

        with transaction.atomic():
            answerset = create_answerset(
                user=user,
                survey_form=active_version,
                metadata=metadata,
            )

            for question_name, answer_value in metadata.items():
                create_answer(
                    answer_set=answerset,
                    question_name=question_name,
                    answer_value=answer_value,
                )

            return Response(
                {"message": _("نظر شما ثبت شد")}, status=status.HTTP_201_CREATED
            )

    def update(self, request, *args, **kwargs):
        try:
            active_version = Survey.objects.get(uuid=kwargs["survey_uuid"]).active_version
            max_responses_allowed = active_version.settings.max_submissions_per_user
            user = request.user

            if max_responses_allowed and user:
                user_submissions = AnswerSet.objects.filter(
                    survey_form=active_version,
                    user=user,
                ).count()

                if user_submissions >= max_responses_allowed:
                    return Response(
                        {"detail": _(f"شما نمی توانید بیش از {max_responses_allowed} پاسخ ارسال کنید.")},
                        status=status.HTTP_403_FORBIDDEN
                    )


            answer_set = self.get_object()

            serializer = self.get_serializer(answer_set, data=request.data)
            serializer.is_valid(raise_exception=True)
            metadata = serializer.validated_data.get("metadata")

            with transaction.atomic():

                answerset = create_answerset(
                    user=user,
                    survey_form=active_version,
                    metadata=metadata,

                )

                for question_name, answer_value in metadata.items():
                    create_answer(
                        answer_set=answerset,
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

            delete_time = timezone.now()

            with transaction.atomic():
                answerset.deleted_at = delete_time
                answerset.save()

                for answer in answerset.answers.all():
                    if answer.deleted_at is None:
                        answer.deleted_at = delete_time
                        answer.save()

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

                for answer in answerset.answers.all():
                    if answer.deleted_at == answerset_delete_time:
                        answer.deleted_at = None
                        answer.save()
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
        queryset = AnswerSet.objects.filter(
            deleted_at__isnull=False,
            survey_form=Survey.objects.get(uuid=kwargs["survey_uuid"]).active_version,
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
