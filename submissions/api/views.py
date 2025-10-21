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
        answer_set = self.get_object()
        answer_set.answers.all().delete()

        serializer = self.get_serializer(answer_set, data=request.data)
        serializer.is_valid(raise_exception=True)
        metadata = serializer.validated_data.get("metadata")
        answerset = serializer.save()

        for question_name, answer_value in metadata.items():
            create_answer(
                answer_set=answerset,
                question_name=question_name,
                answer_value=answer_value,
            )

        return Response(
            {"message": _("نظر شما بروزرسانی شد")}, status=status.HTTP_201_CREATED
        )
