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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "context") and self.context.get("action"):
            action = self.context.get("action")

            if action == "list" or action == "retrieve":
                self.fields.pop("deleted_at")

            elif action == "partial_update":
                allowed_fields = {"title"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            elif action in ["soft_delete", "revoke_delete"]:
                self.fields.clear()


class SurveyFormSerializer(serializers.ModelSerializer):
    parent = serializers.UUIDField(source="parent.uuid", read_only=True)

    class Meta:
        model = SurveyForm
        fields = ["uuid", "version", "description", "metadata", "parent", "deleted_at"]

        read_only_fields = ["uuid", "deleted_at"]
