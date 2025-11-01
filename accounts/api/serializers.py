from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from ..models import User


class UserModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "phone_number",
            "email",
            "role",
            "birth_date",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "context") and self.context.get("action"):
            action = self.context.get("action")

            if action == "create":
                allowed_fields = {"phone_number", "email", "role"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            if (
                action == "me"
                and self.context.get("request")
                and self.context["request"].method == "PATCH"
            ):
                allowed_fields = {"email", "birth_date"}
                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            if action == "partial_update" and self.context.get("request"):
                self.fields["role"].read_only = False
                self.fields["is_active"].read_only = False
                self.fields["is_staff"].read_only = False
                self.fields["is_superuser"].read_only = False

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("ایمیل تکراری است."))
        return value

    def create(self, validated_data):
        return User.objects.create(is_active=False, **validated_data)


class UserSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        label=_("شماره تلفن"),
        max_length=11,
        min_length=11,
        validators=[
            RegexValidator(
                regex=r"^09\d{9}$",
                message=_(
                    "شماره تلفن همراه معتبر ۱۱ رقم دارد و با ۰۹ شروع میشود.مانند ۰۹۱۹۱۲۳۴۵۶۷"
                ),
            )
        ],
        required=True,
    )
    otp = serializers.CharField(
        label=_("کد یکبار مصرف"), min_length=6, max_length=6, required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "context") and self.context.get("action"):
            action = self.context.get("action")

            if action in ["register_resend_otp", "login_resend_otp", "login"]:
                allowed_fields = {"phone_number"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

    def validate(self, data):
        action = self.context.get("action")
        try:
            user = User.objects.get(phone_number=data.get("phone_number"))
            if action in ["register_resend_otp", "register_verify_otp"]:
                if user.is_active:
                    raise serializers.ValidationError(
                        {"phone_number": _("این کاربر قبلاً تأیید شده است")}
                    )
            elif action in ["login", "login_verify_otp", "login_resend_otp"]:
                if not user.is_active:
                    raise serializers.ValidationError(
                        {"phone_number": _("این کاربر فعال نیست")}
                    )

            data["user"] = user
            return data

        except User.DoesNotExist:
            raise NotFound({"phone_number": _("کاربری یافت نشد")})


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)
