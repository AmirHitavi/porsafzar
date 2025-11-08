from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from surveys.api.selectors import (
    get_active_survey_form_by_uuid,
    get_active_version_form,
    get_active_version_form_uuid,
)

from . import services
from .permissions import IsOwner, IsOwnerOrSurveyOwnerOrAdmin, IsSurveyOwnerOrAdmin
from .selectors import (
    get_active_answeset_by_uuid,
    get_all_answersets_for_form,
    get_all_deleted_answersets_for_form,
    get_answerset_by_uuid,
    get_charts_data,
    get_soft_deleted_answerset_by_uuid,
)
from .serializers import AnswerSetSerializer


class AnswerSetViewSet(ModelViewSet):
    serializer_class = AnswerSetSerializer
    http_method_names = ["get", "options", "head", "post", "patch", "delete"]
    lookup_field = "uuid"

    def get_queryset(self):
        survey_uuid = self.kwargs.get("survey_uuid")
        form_uuid = self.request.query_params.get("form_uuid")

        if not form_uuid:
            form_uuid = get_active_version_form_uuid(survey_uuid)

        if self.action == "list_deleted":
            base_queryset = get_all_deleted_answersets_for_form(survey_uuid, form_uuid)
        else:
            base_queryset = get_all_answersets_for_form(survey_uuid, form_uuid)

        return base_queryset.select_related("user", "survey_form")

    def get_permissions(self, *args, **kwargs):
        if self.action == "create":
            return [AllowAny()]
        elif self.action == "partial_update":
            return [IsOwner()]
        elif self.action == "retrieve":
            return [IsOwnerOrSurveyOwnerOrAdmin()]
        else:
            return [IsSurveyOwnerOrAdmin()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        context["survey_uuid"] = self.kwargs.get("survey_uuid")

        if self.action in ["list", "list_deleted"]:
            context["form_uuid"] = self.request.query_params.get("form_uuid")

        if self.action in ["create"]:
            context["one_time_link"] = self.request.query_params.get("token")

        return context

    def create(self, request, *args, **kwargs):
        context = self.get_serializer_context()
        serializer = self.get_serializer(
            data=request.data,
            context=context,
        )
        serializer.is_valid(raise_exception=True)
        answer_set = serializer.save()
        return Response(
            {"message": _("نظر شما ثبت شد."), "data": {"answer_set": answer_set.uuid}},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        context = self.get_serializer_context()
        context["answerset_uuid"] = kwargs.get("uuid")

        serializer = self.get_serializer(
            self.get_object(),
            data=request.data,
            partial=True,
            context=context,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": _("جواب شما بروزرسانی شد.")}, status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        user = request.user

        if user.is_superuser or user.is_staff:
            answer_set = get_answerset_by_uuid(kwargs.get("uuid"))
        else:
            answer_set = get_active_answeset_by_uuid(kwargs.get("uuid"))

        self.check_object_permissions(request, answer_set)
        services.delete_answerset(answer_set, user)

        return Response({"message": _("پرسشنامه حذف شد.")}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def restore(self, request, *args, **kwargs):
        answer_set = get_soft_deleted_answerset_by_uuid(kwargs.get("uuid"))
        self.check_object_permissions(request, answer_set)
        services.restore_answerset(answer_set)

        return Response(
            {"message": _("جواب پرسشنامه بازیابی شد.")}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="archived")
    def list_deleted(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def chart(self, request, *args, **kwargs):
        survey_uuid = self.kwargs.get("survey_uuid")
        form_uuid = self.request.query_params.get("form_uuid")
        if form_uuid:
            form_uuid = form_uuid.strip()
            form = get_active_survey_form_by_uuid(survey_uuid, form_uuid)
        else:
            form = get_active_version_form(survey_uuid)

        data = get_charts_data(form)
        return Response(data)
