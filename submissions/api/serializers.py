from rest_framework import serializers

from ..models import AnswerSet


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

            if action == "me":
                self.fields.pop("metadata")
