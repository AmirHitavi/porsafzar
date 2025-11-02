from rest_framework import serializers

from ..models import AnswerSet
from .services import create_answerset, update_answerset


class AnswerSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerSet
        fields = ["uuid", "user", "survey_form", "metadata", "created_at", "deleted_at"]
        read_only_fields = ["uuid", "user", "survey_form", "created_at", "deleted_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "context") and self.context.get("action"):
            action = self.context.get("action")

            if action == "create":
                allowed_fields = {"metadata"}
                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

    def create(self, validated_data):
        survey_uuid = self.context["survey_uuid"]
        form_uuid = self.context["form_uuid"]
        user = self.context["request"].user or None

        return create_answerset(
            user=user,
            survey_uuid=survey_uuid,
            form_uuid=form_uuid,
            metadata=validated_data["metadata"],
        )

    def update(self, instance, validated_data):
        survey_uuid = self.context["survey_uuid"]
        form_uuid = self.context["form_uuid"]
        answerset_uuid = self.context["answerset_uuid"]

        return update_answerset(
            survey_uuid=survey_uuid,
            form_uuid=form_uuid,
            answerset_uuid=answerset_uuid,
            metadata=validated_data["metadata"],
        )
