from rest_framework import serializers

from ..models import Survey, SurveyForm


class CreateSurveySerializer(serializers.Serializer):
    data = serializers.JSONField(required=True)


class SurveySerializer(serializers.ModelSerializer):
    data = serializers.JSONField(write_only=True)

    class Meta:
        model = Survey
        fields = ["uuid", "title", "created_by", "active_version", "deleted_at", "data"]

        read_only_fields = ["uuid", "deleted_at"]


class SurveyFormSerializer(serializers.ModelSerializer):
    parent = serializers.UUIDField(source="parent.uuid", read_only=True)

    class Meta:
        model = SurveyForm
        fields = ["uuid", "version", "description", "metadata", "parent", "deleted_at"]

        read_only_fields = ["uuid", "deleted_at"]
