from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..models import Survey
from .permissions import IsManagementOrProfessorOrAdmin, IsOwnerOrAdmin
from .serializers import SurveyForm, SurveyFormSerializer, SurveySerializer


class SurveyViewSet(ModelViewSet):

    queryset = Survey.objects.filter(deleted_at__isnull=True)
    serializer_class = SurveySerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "patch", "delete"]

    def get_permissions(self):

        if self.action in ["retrieve", "partial_update", "destroy"]:
            return [IsOwnerOrAdmin(), IsAuthenticated()]

        if self.action in ["create"]:
            return [IsManagementOrProfessorOrAdmin()]

        return [IsAuthenticated()]

    def get_serializer_context(self):
        super().get_serializer_context()
        return {"action": self.action}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def soft_delete(self, request, *args, **kwargs):
        try:
            survey = self.get_object()

            survey.deleted_at = timezone.now()
            survey.save()
            return Response({"detail": _("نظرسنجی حدف شد.")}, status=status.HTTP_200_OK)

        except Survey.DoesNotExist:
            return Response(
                {"detail": _("نظرسنجی یافت نشد")}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def revoke_delete(self, request, *args, **kwargs):
        try:
            survey = Survey.objects.get(uuid=kwargs["uuid"], deleted_at__isnull=False)
            survey.deleted_at = None
            survey.save()
            return Response(
                {"detail": _("نظرسنجی بایگانی شد.")}, status=status.HTTP_200_OK
            )
        except Survey.DoesNotExist:
            return Response(
                {"detail": _("نظرسنجی یافت نشد")}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["get"], url_path="archived")
    def list_deleted(self, request, *args, **kwargs):
        forms = SurveyForm.objects.filter(
            deleted_at__isnull=False, parent__uuid=self.kwargs["uuid"]
        )
        serializer = SurveyFormSerializer(forms, many=True)
        return Response(serializer.data)


class SurveyFormViewSet(ModelViewSet):
    serializer_class = SurveyFormSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "options", "head", "post", "delete"]

    def get_permissions(self):
        if self.action in ["create"]:
            return [IsManagementOrProfessorOrAdmin()]
        else:
            return [AllowAny()]


    def get_queryset(self):
        return SurveyForm.objects.filter(
            deleted_at__isnull=True, parent__uuid=self.kwargs["survey_uuid"]
        )

    # def get_serializer_context(self):
    #     super().get_serializer_context()
    #     return {"action": self.action}

    def perform_create(self, serializer):
        serializer.save(parent__uuid=self.kwargs["survey_uuid"])

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
