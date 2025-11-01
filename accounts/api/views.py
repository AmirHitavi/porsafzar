from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .permissions import IsNotAuthenticated, IsStaffOrSuperUser
from .serializers import LogoutSerializer, UserModelSerializer, UserSerializer
from .services import SendOTP, VerifyOTP, delete_refresh_token

User = get_user_model()


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    http_method_names = ["get", "head", "options", "post", "patch", "delete"]

    def get_permissions(self):
        if self.action in [
            "create",
            "register_verify_otp",
            "register_resend_otp",
            "login",
            "login_verify_otp",
            "login_resend_otp",
        ]:
            return [IsNotAuthenticated()]

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
            return UserSerializer
        elif self.action == "logout":
            return LogoutSerializer
        else:
            return UserModelSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["action"] = self.action
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        otp_message = SendOTP.register_send_otp(user=user)
        return Response(otp_message, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="create/resend-otp")
    def register_resend_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user")
        otp_response, status_code = SendOTP.resend_otp(user=user)
        return Response(otp_response, status=status_code)

    @action(detail=False, methods=["post"], url_path="create/verify-otp")
    def register_verify_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user")
        otp_code = serializer.validated_data.get("otp")
        otp_response, status_code = VerifyOTP.register_verify_otp(
            user=user, otp_code=otp_code
        )
        return Response(otp_response, status=status_code)

    @action(detail=False, methods=["post"])
    def login(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user")
        otp_response, status_code = SendOTP.login_send_otp(user=user)
        return Response(otp_response, status=status_code)

    @action(detail=False, methods=["post"], url_path="login/resend-otp")
    def login_resend_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user")
        otp_response, status_code = SendOTP.resend_otp(user=user)
        return Response(otp_response, status=status_code)

    @action(detail=False, methods=["post"], url_path="login/verify-otp")
    def login_verify_otp(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data.get("user")
        otp_code = serializer.validated_data.get("otp")
        otp_response, status_code = VerifyOTP.login_verify_otp(
            user=user, otp_code=otp_code
        )
        return Response(otp_response, status=status_code)

    @action(detail=False, methods=["post"])
    def logout(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh_token = serializer.validated_data.get("refresh_token")
        logout_response, status_code = delete_refresh_token(refresh=refresh_token)
        return Response(logout_response, status=status_code)

    @action(detail=False, methods=["get", "patch"])
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
