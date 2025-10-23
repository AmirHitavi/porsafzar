import pytest
from django.core.cache import cache
from django.urls import reverse

from conftest import api_client

from ..utils import OTPHandler
from .factories import UserFactory, generate_iranian_phone_number


@pytest.mark.django_db
class TestUserCreation:
    url = reverse("user-list")
    verify_url = reverse("user-register-verify-otp")
    resend_url = reverse("user-register-resend-otp")

    def test_creation_if_phnoe_number_valid_returns_201(self, api_client):

        valid_data = {"phone_number": generate_iranian_phone_number()}

        response = api_client.post(self.url, data=valid_data)

        assert response.status_code == 201
        assert response.data.get("code") == "success"
        assert (
            response.data.get("message")
            == "اکانت موفقیت آمیز ساخته شد. برای شماره تلفن شما کدی ارسال شده است."
        )

    def test_creation_if_phnoe_number_invalid_returns_201(self, api_client):

        invalid_data = {"phone_number": "98121234567"}

        response = api_client.post(self.url, data=invalid_data)

        assert response.status_code == 400

    def test_creation_if_data_valid_returns_201(self, api_client):

        valid_data = {
            "phone_number": generate_iranian_phone_number(),
            "email": "test@email.com",
        }

        response = api_client.post(self.url, data=valid_data)

        assert response.status_code == 201

    def test_cration_if_phone_number_exists_returns_400(self, api_client, normal_user):

        invalid_data = {
            "phone_number": normal_user.phone_number,
        }

        response = api_client.post(self.url, data=invalid_data)

        assert response.status_code == 400

    def test_creation_if_email_exists_returns_400(self, api_client, normal_user):

        invalid_data = {
            "phone_number": generate_iranian_phone_number(),
            "email": normal_user.email,
        }

        response = api_client.post(self.url, data=invalid_data)

        assert response.status_code == 400
        assert response.data.get("code") == "EMAIL_EXISTS"
        assert response.data.get("message") == "کاربر تکراری است."

    def test_cration_if_user_authenticated_returns_401(self, api_client, normal_user):
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

        valid_data = {"phone_number": phone_number, "otp": otp_code}

        response = api_client.post(self.verify_url, data=valid_data)

        assert response.status_code == 200

    def test_verify_if_user_active_returns_400(self, api_client, normal_user):

        valid_data = {"phone_number": normal_user.phone_number, "otp": 123456}

        response = api_client.post(self.verify_url, data=valid_data)

        assert response.status_code == 400
        assert response.data.get("code") == "USER_ALREADY_VERIFIED"
        assert response.data.get("message") == "این کاربر قبلاً تأیید شده است"

    def test_verify_if_otp_wrong_returns_400(self, api_client):
        inactive_user = UserFactory(is_active=False)
        phone_number = inactive_user.phone_number
        otp_code = 123456
        otp_response = OTPHandler.verify_otp(phone_number, otp_code)

        valid_data = {"phone_number": inactive_user.phone_number, "otp": otp_code}

        response = api_client.post(self.verify_url, data=valid_data)

        assert response.status_code == 400
        assert response.data.get("code") == otp_response["code"]
        assert response.data.get("message") == otp_response["message"]

    def test_verify_if_otp_too_many_attemps_returns_400(
        self,
        api_client,
    ):
        inactive_user = UserFactory(is_active=False)
        phone_number = inactive_user.phone_number
        otp_code = 123456

        for _ in range(4):
            otp_response = OTPHandler.verify_otp(phone_number, otp_code)

        valid_data = {"phone_number": inactive_user.phone_number, "otp": otp_code}

        response = api_client.post(self.verify_url, data=valid_data)

        assert response.status_code == 400
        assert response.data.get("code") == otp_response["code"]
        assert response.data.get("message") == otp_response["message"]

    def test_verify_if_user_not_found_returns_404(self, api_client):

        invalid_data = {"phone_number": generate_iranian_phone_number(), "otp": 123456}

        response = api_client.post(self.verify_url, data=invalid_data)

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
        valid_data = {
            "phone_number": inactive_user.phone_number,
        }

        response = api_client.post(self.resend_url, data=valid_data)

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "برای شماره تلفن شما کدی ارسال شده است."

    def test_resend_if_duplicate_returns_400(self, api_client):
        inactive_user = UserFactory(is_active=False)
        valid_data = {
            "phone_number": inactive_user.phone_number,
        }

        api_client.post(self.resend_url, data=valid_data)
        response = api_client.post(self.resend_url, data=valid_data)

        assert response.status_code == 400

    def test_resend_if_user_active_returns_400(self, api_client, normal_user):
        valid_data = {"phone_number": normal_user.phone_number}

        response = api_client.post(self.resend_url, data=valid_data)

        assert response.status_code == 400
        assert response.data.get("code") == "USER_ALREADY_VERIFIED"
        assert response.data.get("message") == "این کاربر قبلاً تأیید شده است"

    def test_resend_if_user_not_exists_returns_404(self, api_client, normal_user):
        invalid_data = {"phone_number": generate_iranian_phone_number()}

        response = api_client.post(self.resend_url, data=invalid_data)

        assert response.status_code == 404
        assert response.data.get("code") == "USER_NOT_EXISTS"
        assert response.data.get("message") == "کاربری یافت نشد"
