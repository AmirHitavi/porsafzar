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

    # def _get_active_form(self, survey_uuid):
    #     try:
    #         survey = Survey.objects.get(uuid=survey_uuid)
    #         active_version = survey.active_version
    #         if active_version:
    #             return active_version
    #         return "Not active"
    #     except Survey.DoesNotExist:
    #         return "Not exists"

    def create(self, request, *args, **kwargs):
        # active_version = self._get_active_form(kwargs["survey_uuid"])

        # if not isinstance(active_version, SurveyForm):
        #     return Response(
        #         {"detail": active_version},
        #         status=status.HTTP_404_NOT_FOUND,
        #     )

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
