from rest_framework import serializers

from ..models import Survey, SurveyForm


class SurveySerializer(serializers.ModelSerializer):

    class Meta:
        model = Survey
        fields = ["uuid", "title", "created_by", "active_version", "deleted_at"]

        read_only_fields = ["uuid", "deleted_at"]

        # def __init__(self, *args, **kwargs):
        #     super().__init__(*args, **kwargs)
        #
        #     if hasattr(self, "context") and self.context.get("action"):
        #         action = self.context.get("action")
        #
        #         if action == "list":
        #            self.fields.pop("deleted_at")


class SurveyFormSerializer(serializers.ModelSerializer):
    parent = serializers.UUIDField(source="parent.uuid", read_only=True)

    class Meta:
        model = SurveyForm
        fields = ["uuid", "version", "description", "metadata", "parent", "deleted_at"]

        read_only_fields = ["uuid", "deleted_at"]
