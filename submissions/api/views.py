from xmlrpc.client import Fault

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from surveys.models import Survey, SurveyForm

from ..models import AnswerSet
from .serializers import AnswerSetSerializer
from .services import create_answer, create_answerset


class AnswerSetViewSet(ModelViewSet):
    queryset = AnswerSet.objects.filter(deleted_at__isnull=True)
    lookup_field = "uuid"
    serializer_class = AnswerSetSerializer
    http_method_names = ["get", "options", "head", "post", "put", "delete"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    def create(self, request, *args, **kwargs):

        active_version = Survey.objects.get(uuid=kwargs["survey_uuid"]).active_version

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        metadata = serializer.validated_data.get("metadata")

        # create answer set
        if self.request and self.request.user.is_authenticated:
            user = request.user
        else:
            user = None

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
            answer_set = self.get_object()
            answer_set.answers.all().delete()

            serializer = self.get_serializer(answer_set, data=request.data)
            serializer.is_valid(raise_exception=True)
            metadata = serializer.validated_data.get("metadata")

            with transaction.atomic():

                answerset = serializer.save()

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
