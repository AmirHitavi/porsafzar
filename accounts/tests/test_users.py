import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from ..utils import OTPHandler
from .factories import UserFactory, generate_iranian_phone_number


@pytest.mark.django_db
class TestUserCreation:
    url = reverse("user-list")
    verify_url = reverse("user-register-verify-otp")
    resend_url = reverse("user-register-resend-otp")

    def test_creation_if_phnoe_number_valid_returns_201(self, api_client):

        data = {"phone_number": generate_iranian_phone_number()}

        response = api_client.post(self.url, data=data)

        assert response.status_code == 201
        assert response.data.get("code") == "success"
        assert (
            response.data.get("message")
            == "اکانت موفقیت آمیز ساخته شد. برای شماره تلفن شما کدی ارسال شده است."
        )

    def test_creation_if_phnoe_number_invalid_returns_201(self, api_client):

        data = {"phone_number": "98121234567"}

        response = api_client.post(self.url, data=data)

        assert response.status_code == 400

    def test_creation_if_data_valid_returns_201(self, api_client):

        data = {
            "phone_number": generate_iranian_phone_number(),
            "email": "test@email.com",
        }

        response = api_client.post(self.url, data=data)

        assert response.status_code == 201

    def test_cration_if_phone_number_exists_returns_400(self, api_client, normal_user):

        data = {
            "phone_number": normal_user.phone_number,
        }

        response = api_client.post(self.url, data=data)

        assert response.status_code == 400

    def test_creation_if_email_exists_returns_400(self, api_client, normal_user):

        data = {
            "phone_number": generate_iranian_phone_number(),
            "email": normal_user.email,
        }

        response = api_client.post(self.url, data=data)

        assert response.status_code == 400
        assert response.data.get("code") == "EMAIL_EXISTS"
        assert response.data.get("message") == "کاربر تکراری است."

    def test_creation_if_user_authenticated_returns_401(self, api_client, normal_user):
        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.url, data={})

        assert response.status_code == 401
        assert response.data.get("code") == "USER_ALREADY_LOGGED_IN"
        assert response.data.get("message") == "کاربر قبلا وارد شده است."

    def test_verify_if_user_authenticated_returns_401(self, api_client, normal_user):
        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.verify_url, data={})

        assert response.status_code == 401
        assert response.data.get("code") == "USER_ALREADY_LOGGED_IN"
        assert response.data.get("message") == "کاربر قبلا وارد شده است."

    def test_verify_if_data_valid_returns_200(self, api_client):
        inactive_user = UserFactory(is_active=False)
        phone_number = inactive_user.phone_number

        OTPHandler.generate_otp(phone_number)
        hashed_phone = OTPHandler._get_hashed_phone(phone_number)
        cache_key = f"otp_{hashed_phone}"
        otp_code = cache.get(cache_key)

        data = {"phone_number": phone_number, "otp": otp_code}

        response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 200

    def test_verify_if_user_active_returns_400(self, api_client, normal_user):

        data = {"phone_number": normal_user.phone_number, "otp": 123456}

        response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 400
        assert response.data.get("code") == "USER_ALREADY_VERIFIED"
        assert response.data.get("message") == "این کاربر قبلاً تأیید شده است"

    def test_verify_if_otp_wrong_returns_400(self, api_client):
        inactive_user = UserFactory(is_active=False)
        otp_code = 123456

        data = {"phone_number": inactive_user.phone_number, "otp": otp_code}

        response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 400
        assert response.data.get("code") == "OTP_EXPIRED"

    def test_verify_if_otp_too_many_attemps_returns_400(self, api_client):
        inactive_user = UserFactory(is_active=False)

        data = {"phone_number": inactive_user.phone_number, "otp": 123456}

        for _ in range(OTPHandler.MAX_ATTEMPTS + 1):
            response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 400
        assert response.data.get("code") == "TOO_MANY_ATTEMPTS"

    def test_verify_if_user_not_found_returns_404(self, api_client):

        data = {"phone_number": generate_iranian_phone_number(), "otp": 123456}

        response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 404
        assert response.data.get("code") == "USER_NOT_EXISTS"
        assert response.data.get("message") == "کاربری یافت نشد"

    def test_resend_if_user_authenticated_returns_401(self, api_client, normal_user):
        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.resend_url, data={})

        assert response.status_code == 401
        assert response.data.get("code") == "USER_ALREADY_LOGGED_IN"
        assert response.data.get("message") == "کاربر قبلا وارد شده است."

    def test_resend_if_data_valid_returns_200(self, api_client):
        inactive_user = UserFactory(is_active=False)
        data = {
            "phone_number": inactive_user.phone_number,
        }

        response = api_client.post(self.resend_url, data=data)

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "برای شماره تلفن شما کدی ارسال شده است."

    def test_resend_if_duplicate_returns_400(self, api_client):
        inactive_user = UserFactory(is_active=False)
        data = {
            "phone_number": inactive_user.phone_number,
        }

        api_client.post(self.resend_url, data=data)
        response = api_client.post(self.resend_url, data=data)

        assert response.status_code == 400

    def test_resend_if_user_active_returns_400(self, api_client, normal_user):
        data = {"phone_number": normal_user.phone_number}

        response = api_client.post(self.resend_url, data=data)

        assert response.status_code == 400
        assert response.data.get("code") == "USER_ALREADY_VERIFIED"
        assert response.data.get("message") == "این کاربر قبلاً تأیید شده است"

    def test_resend_if_user_not_exists_returns_404(self, api_client, normal_user):
        data = {"phone_number": generate_iranian_phone_number()}

        response = api_client.post(self.resend_url, data=data)

        assert response.status_code == 404
        assert response.data.get("code") == "USER_NOT_EXISTS"
        assert response.data.get("message") == "کاربری یافت نشد"


@pytest.mark.django_db
class TestUserUpdate:
    view_name = "user-detail"

    def test_update_if_superuser_valid_data_returns_200(self, api_client, superuser):
        data = {
            "phone_number": generate_iranian_phone_number(),
            "email": "test@gmail.com",
            "role": 5,
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        }

        api_client.force_authenticate(user=superuser)

        response = api_client.patch(
            reverse(self.view_name, args=[superuser.id]), data=data
        )

        assert response.status_code == 200
        assert response.data.get("phone_number") == data["phone_number"]
        assert response.data.get("email") == data["email"]
        assert response.data.get("role") == data["role"]
        assert response.data.get("is_active") == data["is_active"]
        assert response.data.get("is_staff") == data["is_staff"]
        assert response.data.get("is_superuser") == data["is_superuser"]

    def test_update_if_not_super_user_returns_401(self, api_client, normal_user):

        response = api_client.patch(
            reverse(self.view_name, args=[normal_user.id]), data={}
        )

        assert response.status_code == 401

    def test_update_if_phone_number_duplicate_returns_400(
        self, api_client, superuser, normal_user
    ):
        data = {
            "phone_number": superuser.phone_number,
        }

        api_client.force_authenticate(user=superuser)

        response = api_client.patch(
            reverse(self.view_name, args=[normal_user.id]), data=data
        )

        assert response.status_code == 400

    def test_update_if_email_duplicate_returns_400(
        self, api_client, superuser, normal_user
    ):
        data = {
            "email": superuser.email,
        }

        api_client.force_authenticate(user=superuser)

        response = api_client.patch(
            reverse(self.view_name, args=[normal_user.id]), data=data
        )

        assert response.status_code == 400
        assert response.data.get("code") == "EMAIL_EXISTS"
        assert response.data.get("message") == "کاربر با این ایمیل وجود دارد."

    def test_update_if_user_not_exists_returns_404(
        self, api_client, superuser, normal_user
    ):
        # delete normal user
        user_id = normal_user.id
        normal_user.delete()

        api_client.force_authenticate(user=superuser)

        response = api_client.patch(reverse(self.view_name, args=[user_id]), data={})

        assert response.status_code == 404


@pytest.mark.django_db
class TestUserLogin:
    login_url = reverse("user-login")
    verify_url = reverse("user-login-verify-otp")
    resend_url = reverse("user-login-resend-otp")

    def test_login_if_data_valid_returns_200(self, api_client, normal_user):
        data = {
            "phone_number": normal_user.phone_number,
        }

        response = api_client.post(self.login_url, data=data)

        assert response.status_code == 200

    def test_login_if_user_not_active_returns_401(self, api_client):
        inactive_user = UserFactory(is_active=False)

        data = {
            "phone_number": inactive_user.phone_number,
        }

        response = api_client.post(self.login_url, data=data)

        assert response.status_code == 401
        assert response.data.get("code") == "USER_NOT_ACTIVE"
        assert response.data.get("message") == "کاربر فعال نیست."

    def test_login_if_duplicate_request_returns_400(self, api_client, normal_user):
        data = {
            "phone_number": normal_user.phone_number,
        }

        api_client.post(self.login_url, data=data)
        response = api_client.post(self.login_url, data=data)

        assert response.status_code == 400

    def test_login_if_user_not_exists_returns_404(self, api_client):
        data = {"phone_number": generate_iranian_phone_number()}

        response = api_client.post(self.login_url, data=data)

        assert response.status_code == 404
        assert response.data.get("code") == "USER_NOT_EXISTS"
        assert response.data.get("message") == "کاربری یافت نشد"

    def test_login_if_user_authenticated_returns_401(self, api_client, normal_user):
        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.login_url, data={})

        assert response.status_code == 401
        assert response.data.get("code") == "USER_ALREADY_LOGGED_IN"
        assert response.data.get("message") == "کاربر قبلا وارد شده است."

    def test_verify_if_user_authenticated_returns_401(self, api_client, normal_user):
        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.verify_url, data={})

        assert response.status_code == 401
        assert response.data.get("code") == "USER_ALREADY_LOGGED_IN"
        assert response.data.get("message") == "کاربر قبلا وارد شده است."

    def test_verify_if_data_valid_returns_200(self, api_client, normal_user):
        phone_number = normal_user.phone_number

        OTPHandler.generate_otp(phone_number)
        hashed_phone = OTPHandler._get_hashed_phone(phone_number)
        cache_key = f"otp_{hashed_phone}"
        otp_code = cache.get(cache_key)

        data = {"phone_number": phone_number, "otp": otp_code}

        response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 200

    def test_verify_if_user_not_active_returns_401(self, api_client):
        inactive_user = UserFactory(is_active=False)

        data = {"phone_number": inactive_user.phone_number, "otp": 123456}

        response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 401
        assert response.data.get("code") == "USER_NOT_ACTIVE"
        assert response.data.get("message") == "کاربر فعال نیست."

    def test_verify_if_otp_wrong_returns_400(self, api_client, normal_user):
        data = {"phone_number": normal_user.phone_number, "otp": 123456}

        response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 400
        assert response.data.get("code") == "OTP_EXPIRED"

    def test_verify_if_otp_too_many_attemps_returns_400(self, api_client, normal_user):
        data = {"phone_number": normal_user.phone_number, "otp": 123456}

        for _ in range(OTPHandler.MAX_ATTEMPTS + 1):
            response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 400
        assert response.data.get("code") == "TOO_MANY_ATTEMPTS"

    def test_verify_if_user_not_exists_returns_404(self, api_client):
        data = {"phone_number": generate_iranian_phone_number(), "otp": 123456}

        response = api_client.post(self.verify_url, data=data)

        assert response.status_code == 404
        assert response.data.get("code") == "USER_NOT_EXISTS"
        assert response.data.get("message") == "کاربری یافت نشد"

    def test_resend_if_user_authenticated_returns_401(self, api_client, normal_user):
        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.resend_url, data={})

        assert response.status_code == 401
        assert response.data.get("code") == "USER_ALREADY_LOGGED_IN"
        assert response.data.get("message") == "کاربر قبلا وارد شده است."

    def test_resend_if_data_valid_returns_200(self, api_client, normal_user):
        data = {
            "phone_number": normal_user.phone_number,
        }

        response = api_client.post(self.resend_url, data=data)

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "برای شماره تلفن شما کدی ارسال شده است."

    def test_resend_if_duplicate_returns_400(self, api_client, normal_user):
        data = {
            "phone_number": normal_user.phone_number,
        }

        api_client.post(self.resend_url, data=data)
        response = api_client.post(self.resend_url, data=data)

        assert response.status_code == 400

    def test_resend_if_user_not_active_returns_401(self, api_client):
        inactive_user = UserFactory(is_active=False)

        data = {"phone_number": inactive_user.phone_number}

        response = api_client.post(self.resend_url, data=data)

        assert response.status_code == 401
        assert response.data.get("code") == "USER_NOT_ACTIVE"
        assert response.data.get("message") == "کاربر فعال نیست."

    def test_resend_if_user_not_exists_returns_404(self, api_client):
        data = {"phone_number": generate_iranian_phone_number()}

        response = api_client.post(self.resend_url, data=data)

        assert response.status_code == 404
        assert response.data.get("code") == "USER_NOT_EXISTS"
        assert response.data.get("message") == "کاربری یافت نشد"


@pytest.mark.django_db
class TestUserLogout:

    url = reverse("user-logout")

    def test_logout_if_data_valid_returns_200(self, api_client, normal_user):
        data = {
            "refresh": str(RefreshToken.for_user(normal_user)),
        }

        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.url, data=data)

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "خروج موفقیت آمیز بود."

    def test_logout_if_refresh_token_missing_returns_401(self, api_client, normal_user):
        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.url, data={})

        assert response.status_code == 401
        assert response.data.get("code") == "REFRESH_TOKEN_NOT_EXISTS"
        assert response.data.get("message") == "رفرش توکن ارسال نشده است."

    def test_logout_if_refresh_token_invalid_returns_400(self, api_client, normal_user):
        data = {"refresh": "invalid"}

        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.url, data=data)

        assert response.status_code == 400
        assert response.data["error"] == "خطا در خروج"

    def test_logout_if_user_not_authenticated_returns_401(self, api_client):

        response = api_client.post(self.url, data={})

        assert response.status_code == 401

    def test_logout_if_refresh_token_already_blacklisted_returns_400(
        self, api_client, normal_user
    ):
        refresh = RefreshToken.for_user(normal_user)
        refresh.blacklist()

        data = {"refresh": str(refresh)}

        api_client.force_authenticate(user=normal_user)

        response = api_client.post(self.url, data=data)

        assert response.status_code == 400
        assert response.data["error"] == "خطا در خروج"


@pytest.mark.django_db
class TestUserMe:
    url = reverse("user-me")

    def test_me_get_if_user_authenticated_returns_200(self, api_client, normal_user):

        api_client.force_authenticate(user=normal_user)

        response = api_client.get(self.url)

        assert response.status_code == 200
        assert response.data.get("phone_number") == normal_user.phone_number

    def test_me_get_if_user_not_authenticated_returns_401(self, api_client):

        response = api_client.get(self.url)

        assert response.status_code == 401

    def test_me_patch_if_data_valid_returns_200(self, api_client, normal_user):
        data = {"email": "test@gmail.com", "birth_date": timezone.now().date()}

        api_client.force_authenticate(user=normal_user)

        response = api_client.patch(self.url, data=data)

        assert response.status_code == 200
        assert response.data.get("email") == data.get("email")

    def test_me_patch_if_data_invalid_returns_400(self, api_client, normal_user):
        data = {"birth_date": timezone.now()}

        api_client.force_authenticate(user=normal_user)

        response = api_client.patch(self.url, data=data)

        assert response.status_code == 400

    def test_me_patch_if_email_duplicate_returns_400(self, api_client, normal_user):
        data = {"email": normal_user.email}

        api_client.force_authenticate(user=normal_user)

        response = api_client.patch(self.url, data=data)

        assert response.status_code == 400
        assert response.data.get("code") == "EMAIL_EXISTS"
        assert response.data.get("message") == "آدرس ایمیل دیگری را وارد کنید."

    def test_me_patch_if_user_not_authenticated_returns_401(self, api_client):

        response = api_client.patch(self.url, data={})

        assert response.status_code == 401
