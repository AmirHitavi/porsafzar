from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from ..utils import OTPHandler
from .permissions import IsStaffOrSuperUser
from .serializers import UserOTPSerializer, UserSerializer

User = get_user_model()


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    http_method_names = ["get", "head", "options", "post", "patch", "delete"]

    def _success_response(self, message, code, status_code, data=None):
        return Response(
            {"code": code, "message": message, "data": data or {}},
            status=status_code,
        )

    def _error_response(self, message, code, status_code, errors=None):
        return Response(
            {"code": code, "message": message, "errors": errors or {}},
            status=status_code,
        )

    def _check_user_not_authenticated(self):
        if self.request.user and self.request.user.is_authenticated:
            return self._error_response(
                code="USER_ALREADY_LOGGED_IN",
                message=_("کاربر قبلا وارد شده است."),
                errors={},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        return None

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
            return [IsStaffOrSuperUser()]

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
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    def create(self, request, *args, **kwargs):
        check_response = self._check_user_not_authenticated()
        if check_response is not None:
            return check_response

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        phone_number = validated_data.get("phone_number")
        email = validated_data.get("email", None)
        if email is not None and User.objects.filter(email=email).exists():
            return self._error_response(
                message=_("کاربر تکراری است."),
                code="EMAIL_EXISTS",
                errors={"email": [_("کاربری با این آدرس ایمیل وجود دارد.")]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create(is_active=False, **validated_data)
        data = ({"phone_number": phone_number, "user_id": user.id},)

        otp_response = OTPHandler.generate_otp(phone_number)

        if otp_response["status"] == "success":
            return self._success_response(
                code="success",
                message=_(
                    "اکانت موفقیت آمیز ساخته شد. برای شماره تلفن شما کدی ارسال شده است."
                ),
                data=data,
                status_code=status.HTTP_201_CREATED,
            )

        # else:
        #     return self._error_response(
        #         code="failure",
        #         message=_(
        #             "اکانت موفقیت آمیز ساخته شد اما در ارسال کد به تلفن همراه شما به مشکل خوردیم."
        #             "لطفا دوباره تلاش بکنید."
        #         ),
        #         data=data,
        #         status_code=status.HTTP_201_CREATED,
        #     )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email", None)

        if email and User.objects.filter(email=email).exists():
            return self._error_response(
                code="EMAIL_EXISTS",
                message=_("کاربر با این ایمیل وجود دارد."),
                errors={},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="create/verify-otp")
    def register_verify_otp(self, request, *args, **kwargs):
        check_response = self._check_user_not_authenticated()
        if check_response is not None:
            return check_response

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")
        otp = serializer.validated_data.get("otp")

        try:
            user = User.objects.get(phone_number=phone_number)

            if user.is_active:
                return self._error_response(
                    code="USER_ALREADY_VERIFIED",
                    message=_("این کاربر قبلاً تأیید شده است"),
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            otp_response = OTPHandler.verify_otp(phone_number, otp)

            refresh = RefreshToken.for_user(user)

            if otp_response["status"] == "success":
                user.is_active = True
                user.last_login = timezone.now()
                user.save()

                return self._success_response(
                    code="SUCCESS",
                    message=_("اکانت شما با موفقیت تایید شد."),
                    data={
                        "user_id": user.id,
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    status_code=status.HTTP_200_OK,
                )

            elif otp_response["status"] == "error":
                return self._error_response(
                    code=otp_response["code"],
                    message=otp_response["message"],
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return self._error_response(
                code="USER_NOT_EXISTS",
                message="کاربری یافت نشد",
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"], url_path="create/resend-otp")
    def register_resend_otp(self, request, *args, **kwargs):
        check_response = self._check_user_not_authenticated()
        if check_response is not None:
            return check_response

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")

        try:
            user = User.objects.get(phone_number=phone_number)

            if user.is_active:
                return self._error_response(
                    code="USER_ALREADY_VERIFIED",
                    message=_("این کاربر قبلاً تأیید شده است"),
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            otp_response = OTPHandler.generate_otp(phone_number)

            if otp_response["status"] == "success":
                return self._success_response(
                    code="SUCCESS",
                    message=_("برای شماره تلفن شما کدی ارسال شده است."),
                    data={"phone_number": phone_number, "user_id": user.id},
                    status_code=status.HTTP_200_OK,
                )

            elif otp_response["status"] == "error":
                return self._error_response(
                    code=otp_response["code"],
                    message=otp_response["message"],
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except User.DoesNotExist:
            return self._error_response(
                code="USER_NOT_EXISTS",
                message="کاربری یافت نشد",
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"])
    def login(self, request, *args, **kwargs):
        check_response = self._check_user_not_authenticated()
        if check_response is not None:
            return check_response

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")

        try:
            user = User.objects.get(phone_number=phone_number)

            if not user.is_active:
                return self._error_response(
                    code="USER_NOT_ACTIVE",
                    message=_("کاربر فعال نیست."),
                    errors={},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            otp_response = OTPHandler.generate_otp(phone_number)

            if otp_response["status"] == "success":
                return self._success_response(
                    code="SUCCESS",
                    message=otp_response["message"],
                    data={"phone_number": phone_number, "user_id": user.id},
                    status_code=status.HTTP_200_OK,
                )

            else:
                return self._error_response(
                    code=otp_response["code"],
                    message=otp_response["message"],
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except User.DoesNotExist:
            return self._error_response(
                code="USER_NOT_EXISTS",
                message="کاربری یافت نشد",
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"], url_path="login/verify-otp")
    def login_verify_otp(self, request, *args, **kwargs):
        check_response = self._check_user_not_authenticated()
        if check_response is not None:
            return check_response

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")
        otp = serializer.validated_data.get("otp")

        try:
            user = User.objects.get(phone_number=phone_number)

            if not user.is_active:
                return self._error_response(
                    code="USER_NOT_ACTIVE",
                    message=_("کاربر فعال نیست."),
                    errors={},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            otp_response = OTPHandler.verify_otp(phone_number, otp)

            refresh = RefreshToken.for_user(user)

            if otp_response["status"] == "success":
                user.last_login = timezone.now()
                user.save(update_fields=["last_login"])

                return self._success_response(
                    code="SUCCESS",
                    message=otp_response["message"],
                    data={
                        "user_id": user.id,
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    status_code=status.HTTP_200_OK,
                )

            elif otp_response["status"] == "error":
                return self._error_response(
                    code=otp_response["code"],
                    message=otp_response["message"],
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except User.DoesNotExist:
            return self._error_response(
                code="USER_NOT_EXISTS",
                message="کاربری یافت نشد",
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"], url_path="login/resend-otp")
    def login_resend_otp(self, request, *args, **kwargs):
        check_response = self._check_user_not_authenticated()
        if check_response is not None:
            return check_response

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")

        try:
            user = User.objects.get(phone_number=phone_number)

            if not user.is_active:
                return self._error_response(
                    code="USER_NOT_ACTIVE",
                    message=_("کاربر فعال نیست."),
                    errors={},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            otp_response = OTPHandler.generate_otp(phone_number)

            if otp_response["status"] == "success":
                return self._success_response(
                    code="SUCCESS",
                    message=_("برای شماره تلفن شما کدی ارسال شده است."),
                    data={"phone_number": phone_number, "user_id": user.id},
                    status_code=status.HTTP_200_OK,
                )

            elif otp_response["status"] == "error":
                return self._error_response(
                    code=otp_response["code"],
                    message=otp_response["message"],
                    errors={},
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        except User.DoesNotExist:
            return self._error_response(
                code="USER_NOT_EXISTS",
                message="کاربری یافت نشد",
                errors={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"])
    def logout(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")

            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return self._success_response(
                    code="SUCCESS",
                    message=_("خروج موفقیت آمیز بود."),
                    data={},
                    status_code=status.HTTP_200_OK,
                )
            else:
                return self._error_response(
                    code="REFRESH_TOKEN_NOT_EXISTS",
                    message=_("رفرش توکن ارسال نشده است."),
                    errors={},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
        except Exception:
            return Response(
                {"error": _("خطا در خروج")}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["get", "patch"])
    def me(self, request, *args, **kwargs):
        user = request.user

        if request.method == "GET":
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == "PATCH":
            serializer = self.get_serializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data.get("email")
            if email:
                if user.email == email:
                    pass

                elif User.objects.filter(email=email).exists():
                    return self._error_response(
                        message=_("آدرس ایمیل دیگری را وارد کنید."),
                        code="EMAIL_EXISTS",
                        errors={"email": [_("کاربری با این آدرس ایمیل وجود دارد.")]},
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
