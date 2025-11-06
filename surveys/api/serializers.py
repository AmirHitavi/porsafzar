from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import OneTimeLink, Survey, SurveyForm, SurveyFormSettings, TargetAudience
from .selectors import get_survey_by_uuid
from .services import create_survey, create_survey_form

User = get_user_model()


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

            if action == "create":
                allowed_fields = {"data"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            if action == "list" or action == "retrieve":
                self.fields.pop("deleted_at")

            elif action == "partial_update":
                allowed_fields = {"title"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            elif action in ["destroy", "restore"]:
                self.fields.clear()

    def get_forms(self, obj: Survey):
        action = self.context.get("action")
        if action in ["restore", "list_deleted"]:
            forms = getattr(obj, "prefetched_deleted_forms", None)
            if forms is None:
                forms = SurveyForm.deleted_objects.filter(parent=obj)

        else:
            forms = getattr(obj, "prefetched_active_forms", None)
            if forms is None:
                forms = SurveyForm.active_objects.filter(parent=obj)

        return [
            {
                "version": form.version,
                "uuid": form.uuid,
                "description": form.description,
            }
            for form in forms
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        survey_json = validated_data.get("data")

        survey = create_survey(user=user, title=survey_json.get("title", None))
        create_survey_form(
            parent=survey,
            json_data=survey_json,
            version=1,
            description=survey_json.get("description", None),
        )

        return survey

    def get_created_at(self, obj: Survey):
        now = obj.created_at
        return now.strftime("%Y-%m-%d: %H:%M:%S")

    def get_deleted_at(self, obj: Survey):
        if obj.deleted_at:
            return obj.deleted_at.strftime("%Y-%m-%d: %H:%M:%S")


class SurveyFormSerializer(serializers.ModelSerializer):
    target = serializers.PrimaryKeyRelatedField(
        queryset=TargetAudience.objects.all(), required=False, allow_null=True
    )
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
            "target",
            "created_at",
            "deleted_at",
        ]

        read_only_fields = ["uuid", "parent", "created_at", "deleted_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "context") and self.context.get("action"):
            action = self.context.get("action")

            if action == "list":
                allowed_fields = {"uuid", "version", "description", "target"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            elif action == "retrieve":
                allowed_fields = {
                    "version",
                    "description",
                    "metadata",
                    "target",
                    "created_at",
                }

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            elif action == "create":
                allowed_fields = {"version", "description", "metadata", "target"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            elif action in ["restore", "activate_form", "validate_add_target"]:
                self.fields.clear()

            elif action == "add_target_audience":
                allowed_fields = {"target"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

    def get_created_at(self, obj: Survey):
        return obj.created_at.strftime("%Y-%m-%d: %H:%M:%S")

    def get_deleted_at(self, obj: Survey):
        if obj.deleted_at:
            return obj.deleted_at.strftime("%Y-%m-%d: %H:%M:%S")

    def create(self, validated_data):
        survey_uuid = self.context["survey_uuid"]
        parent = get_survey_by_uuid(survey_uuid)

        version = self.validated_data.get("version")
        description = self.validated_data.get("description", None)
        metadata = self.validated_data.get("metadata")
        target = self.validated_data.get("target", None)

        try:
            return create_survey_form(
                parent=parent,
                json_data=metadata,
                version=version,
                description=description,
                target=target,
            )
        except IntegrityError:
            raise serializers.ValidationError(
                {
                    "message": _("فرم پرسشنامه با این شماره وجود دارد."),
                }
            )


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


class TargetAudienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetAudience
        fields = [
            "id",
            "name",
            "description",
            "roles",
            "include_phone_numbers",
            "exclude_phone_numbers",
        ]

    def validate_include_phone_numbers(self, value):
        phone_numbers = {str(num).strip() for num in (value or [])}
        errors = []
        for phone_number in phone_numbers:
            if not User.objects.filter(phone_number=phone_number).exists():
                errors.append(_(f"{phone_number} چنین شماره‌ای وجود ندارد."))
        if errors:
            raise serializers.ValidationError(errors)
        return list(phone_numbers)

    def validate_exclude_phone_numbers(self, value):
        phone_numbers = {str(num).strip() for num in (value or [])}
        errors = []
        for phone_number in phone_numbers:
            if not User.objects.filter(phone_number=phone_number).exists():
                errors.append(_(f"{phone_number} چنین شماره‌ای وجود ندارد."))
        if errors:
            raise serializers.ValidationError(errors)
        return list(phone_numbers)

    def validate(self, attrs):
        include = {str(num).strip() for num in attrs.get("include_phone_numbers", [])}
        exclude = {str(num).strip() for num in attrs.get("exclude_phone_numbers", [])}
        common = include & exclude
        if common:
            raise serializers.ValidationError(
                {
                    "include_phone_numbers": _(
                        f"شماره‌های {', '.join(common)} نمی‌توانند هم‌زمان در لیست مجاز و غیرمجاز باشند."
                    )
                }
            )
        return attrs


class OneTimeLinkSerializer(serializers.ModelSerializer):
    numbers = serializers.IntegerField(
        write_only=True, validators=[MinValueValidator(1)]
    )

    class Meta:
        model = OneTimeLink
        fields = ["numbers", "token", "is_used", "created_at"]
        read_only_fields = ["token", "is_used", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "context") and self.context.get("action"):
            action = self.context["action"]

            if action == "create":
                allowed_fields = {"numbers"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)
