from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..models import Survey
from .permissions import IsManagementOrProfessorOrAdmin, IsOwnerOrAdmin
from .serializers import SurveySerializer


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

        return [AllowAny()]

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
