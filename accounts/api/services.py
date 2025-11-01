from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import User
from ..utils import OTPHandler


class SendOTP:

    @staticmethod
    def _send_otp(user: User):
        return OTPHandler.generate_otp(user.phone_number)

    @staticmethod
    def register_send_otp(user: User) -> dict:
        response = SendOTP._send_otp(user)
        if response.get("status") == "success":
            message = _("اکانت ساخته شد و کد تایید ارسال شد.")
        else:
            message = "اکانت موفقیت آمیز ساخته شد اما در ارسال کد به تلفن همراه شما به مشکل خوردیم."
        return {"message": message}

    @staticmethod
    def resend_otp(user: User) -> tuple:
        response = SendOTP._send_otp(user)
        if response.get("status") == "success":
            return {
                "message": _("برای شماره تلفن شما کدی ارسال شده است.")
            }, status.HTTP_200_OK
        else:
            return {"message": response.get("message")}, status.HTTP_400_BAD_REQUEST

    @staticmethod
    def login_send_otp(user: User) -> tuple:
        response = SendOTP._send_otp(user)
        if response.get("status") == "success":
            return {
                "message": _("برای ورود کد ارسال شده به تلفن خود را وارد کنید.")
            }, status.HTTP_200_OK
        else:
            return {"message": response.get("message")}, status.HTTP_400_BAD_REQUEST


class VerifyOTP:

    @staticmethod
    def create_refresh_token(user: User):
        return RefreshToken.for_user(user)

    @staticmethod
    def _verify_otp(user: User, otp_code: str):
        return OTPHandler.verify_otp(user.phone_number, otp_code)

    @staticmethod
    def register_verify_otp(user: User, otp_code: str) -> tuple:
        response = VerifyOTP._verify_otp(user, otp_code)

        if response.get("status") == "success":
            user.is_active = True
            user.last_login = timezone.now()
            user.save(update_fields=["is_active", "last_login"])

            tokens = VerifyOTP.create_refresh_token(user)

            return {
                "message": _("اکانت شما با موفقیت تایید شد."),
                "access": str(tokens.access_token),
                "refresh": str(tokens),
            }, status.HTTP_200_OK
        else:
            return {"message": response.get("message")}, status.HTTP_400_BAD_REQUEST

    @staticmethod
    def login_verify_otp(user: User, otp_code: str) -> tuple:
        response = VerifyOTP._verify_otp(user, otp_code)

        if response.get("status") == "success":
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            tokens = VerifyOTP.create_refresh_token(user)

            return {
                "message": _("با موفقیت وارد اکانت شدید."),
                "access": str(tokens.access_token),
                "refresh": str(tokens),
            }, status.HTTP_200_OK
        else:
            return {"message": response.get("message")}, status.HTTP_400_BAD_REQUEST


def delete_refresh_token(refresh: RefreshToken):
    try:
        token = RefreshToken(refresh)
        token.blacklist()
        return (
            {"detail": _("خروج موفقیت‌آمیز بود.")},
            status.HTTP_200_OK,
        )
    except Exception:
        return (
            {"detail": _("رفرش توکن نامعتبر است یا قبلاً باطل شده است.")},
            status.HTTP_400_BAD_REQUEST,
        )
