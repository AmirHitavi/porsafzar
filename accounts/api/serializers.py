from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import User


class UserSerializer(serializers.ModelSerializer):
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
            "role",
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

            if action == "register":
                allowed_fields = {"phone_number"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)

            if action == "logout":
                self.fields.clear()


class UserOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
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
    otp = serializers.CharField(min_length=6, max_length=6, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self, "context") and self.context.get("action"):
            action = self.context.get("action")

            if action in ["register_resend_otp", "login_resend_otp"]:
                allowed_fields = {"phone_number"}

                for field in set(self.fields) - allowed_fields:
                    self.fields.pop(field)


class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
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
