from rest_framework import serializers

from ..models import Survey, SurveyForm, SurveyFormSettings


class CreateSurveySerializer(serializers.Serializer):
    data = serializers.JSONField(required=True)


class SurveyFormSerializer(serializers.ModelSerializer):
    parent = serializers.UUIDField(source="parent.uuid", read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SurveyForm
        fields = [
            "uuid",
            "version",
            "description",
            "metadata",
            "parent",
            "created_at",
            "deleted_at",
        ]

        read_only_fields = ["uuid", "parent", "created_at", "deleted_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "context") and self.context.get("action"):
            action = self.context.get("action")

            if action == "list":
                allowed_fields = {"uuid", "version", "description"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            elif action == "retrieve":
                allowed_fields = {"version", "description", "metadata", "created_at"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            elif action == "create":
                allowed_fields = {"version", "description", "metadata"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            elif action == ["soft_delete", "revoke_delete"]:
                self.fields.clear()

    def get_created_at(self, obj: Survey):
        return obj.created_at.strftime("%Y-%m-%d: %H:%M:%S")

    def get_deleted_at(self, obj: Survey):
        if obj.deleted_at:
            return obj.deleted_at.strftime("%Y-%m-%d: %H:%M:%S")


class SurveySerializer(serializers.ModelSerializer):
    data = serializers.JSONField(write_only=True)
    active_version = serializers.ReadOnlyField(source="active_version.uuid")
    forms = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Survey
        fields = [
            "id",
            "uuid",
            "title",
            "created_by",
            "active_version",
            "deleted_at",
            "data",
            "created_at",
            "forms",
        ]

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

    def get_forms(self, obj: Survey):
        forms = obj.forms.filter(deleted_at__isnull=True).order_by("-created_at")

        return [
            {
                "uuid": form.uuid,
                "version": form.version,
                "description": form.description,
            }
            for form in forms
        ]

    def get_created_at(self, obj: Survey):
        now = obj.created_at
        return now.strftime("%Y-%m-%d: %H:%M:%S")

    def get_deleted_at(self, obj: Survey):
        if obj.deleted_at:
            return obj.deleted_at.strftime("%Y-%m-%d: %H:%M:%S")


class SurveyFormSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = SurveyFormSettings
        fields = [
            "is_active",
            "start_date",
            "end_date",
            "max_submissions_per_user",
            "is_editable",
        ]
