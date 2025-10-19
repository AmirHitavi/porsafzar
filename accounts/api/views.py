from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from ..utils import OTPHandler
from .serializers import UserOTPSerializer, UserSerializer

User = get_user_model()


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_permissions(self):
        if self.action in [
            "create",
            "register_verify_otp",
            "register_resend_otp",
            "login",
            "login_verify_otp",
            "login_resend_otp",
        ]:
            return [AllowAny()]

        elif self.action in ["logout", "me"]:
            return [IsAuthenticated()]

        else:
            return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action in [
            "register_verify_otp",
            "register_resend_otp",
            "login_verify_otp",
            "login_resend_otp",
            "login",
        ]:
            return UserOTPSerializer
        else:
            return UserSerializer

    def get_serializer_context(self):
        super().get_serializer_context()
        return {"action": self.action}

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        try:
            if User.objects.filter(phone_number=phone_number).exists():
                return Response(
                    {
                        "error": _("کاربری با این شماره تلفن وجود دارد."),
                        "code": "USER_ALREADY_EXISTS",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = User.objects.create(phone_number=phone_number, is_active=False)

            otp_response = OTPHandler.generate_otp(phone_number)

            if otp_response["status"] == "success":
                return Response(
                    {
                        "message": _(
                            "اکانت موفقیت آمیز ساخته شد. برای شماره تلفن شما کدی ارسال شده است."
                        ),
                        "phone_number": phone_number,
                        "user_id": user.id,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "message": _(
                            "اکانت موفقیت آمیز ساخته شد اما در ارسال کد به تلفن همراه شما به مشکل خوردیم."
                            "لطفا دوباره تلاش بکنید."
                        ),
                        "phone_number": phone_number,
                        "user_id": user.id,
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception:
            return Response(
                {"error": "مشکل در ساخت اکانت کاربری"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"], url_path="create/verify-otp")
    def register_verify_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")
        otp = serializer.validated_data.get("otp")

        try:
            user = User.objects.get(phone_number=phone_number)

            if user.is_active:
                return Response(
                    {
                        "error": _("این کاربر قبلاً تأیید شده است"),
                        "code": "USER_ALREADY_VERIFIED",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            otp_response = OTPHandler.verify_otp(phone_number, otp)

            refresh = RefreshToken.for_user(user)

            if otp_response["status"] == "success":
                user.is_active = True
                user.save()

                return Response(
                    {
                        "message": otp_response["message"],
                        "code": otp_response["code"],
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                        "user_id": user.id,
                    },
                    status=status.HTTP_200_OK,
                )
            elif otp_response["status"] == "error":
                return Response(
                    {"message": otp_response["message"], "code": otp_response["code"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return Response(
                {
                    "error": _("کاربری با این شماره همراه وجود ندارد"),
                    "code": "USER_NOT_EXISTS",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"], url_path="create/resend-otp")
    def register_resend_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")

        try:
            user = User.objects.get(phone_number=phone_number)

            if user.is_active:
                return Response(
                    {
                        "error": _("این کاربر قبلاً تأیید شده است"),
                        "code": "USER_ALREADY_VERIFIED",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            otp_response = OTPHandler.generate_otp(phone_number)

            if otp_response["status"] == "success":
                return Response(
                    {
                        "message": _("برای شماره تلفن شما کدی ارسال شده است."),
                        "phone_number": phone_number,
                        "user_id": user.id,
                    },
                    status=status.HTTP_201_CREATED,
                )
            elif otp_response["status"] == "error":
                return Response(
                    {"message": otp_response["message"], "code": otp_response["code"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except User.DoesNotExist:
            return Response(
                {
                    "error": _("کاربری با این شماره همراه وجود ندارد"),
                    "code": "USER_NOT_EXISTS",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"])
    def login(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")

        try:
            user = User.objects.get(phone_number=phone_number)

            if not user.is_active:
                return Response(
                    {"error": _("کاربر فعال نیست"), "code": "USER_NOT_ACTIVE"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            otp_response = OTPHandler.generate_otp(phone_number)

            if otp_response["status"] == "success":
                return Response(
                    {
                        "message": otp_response["message"],
                        "phone_number": phone_number,
                        "user_id": user.id,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:

                return Response(
                    {
                        "message": otp_response["message"],
                        "phone_number": phone_number,
                        "user_id": user.id,
                    },
                    status=status.HTTP_200_OK,
                )

        except User.DoesNotExist:
            return Response(
                {
                    "error": _("کاربری با این شماره تلفن وجود ندارد."),
                    "code": "USER_NOT_EXISTS",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"], url_path="login/verify-otp")
    def login_verify_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")
        otp = serializer.validated_data.get("otp")

        try:
            user = User.objects.get(phone_number=phone_number)

            otp_response = OTPHandler.verify_otp(phone_number, otp)

            refresh = RefreshToken.for_user(user)

            if otp_response["status"] == "success":
                user.is_active = True
                user.save()

                return Response(
                    {
                        "message": otp_response["message"],
                        "code": otp_response["code"],
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                        "user_id": user.id,
                    },
                    status=status.HTTP_200_OK,
                )
            elif otp_response["status"] == "error":
                return Response(
                    {"message": otp_response["message"], "code": otp_response["code"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return Response(
                {
                    "error": _("کاربری با این شماره همراه وجود ندارد"),
                    "code": "USER_NOT_EXISTS",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"], url_path="login/resend-otp")
    def login_resend_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")

        try:
            user = User.objects.get(phone_number=phone_number)

            otp_response = OTPHandler.generate_otp(phone_number)

            if otp_response["status"] == "success":
                return Response(
                    {
                        "message": _("برای شماره تلفن شما کدی ارسال شده است."),
                        "phone_number": phone_number,
                        "user_id": user.id,
                    },
                    status=status.HTTP_201_CREATED,
                )
            elif otp_response["status"] == "error":
                return Response(
                    {"message": otp_response["message"], "code": otp_response["code"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except User.DoesNotExist:
            return Response(
                {
                    "error": _("کاربری با این شماره همراه وجود ندارد"),
                    "code": "USER_NOT_EXISTS",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"])
    def logout(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")

            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response(
                    {"detail": _("خروج موفقیت آمیز بود.")}, status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {"error": _("خطا در خروج")}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated]
    )
    def me(self, request, *args, **kwargs):
        user = request.user

        if request.method == "GET":
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == "PATCH":
            serializer = self.get_serializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
