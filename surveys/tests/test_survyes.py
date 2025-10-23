import pytest
import json
from django.urls import reverse
import os
from config.env import BASE_DIR
from conftest import api_client


@pytest.mark.django_db
class TestSurveyCreation:
    url = reverse("survey-list")

    def test_if_data_valid_returns_200(self, api_client, superuser, professor, management):
        file_path = os.path.join(BASE_DIR, "surveys", "tests", "example.json")

        with open(file_path) as f:
            data = {"data": f.read()}

        users = [superuser, professor, management]
        for user in users:
            api_client.force_authenticate(user=user)

            response = api_client.post(self.url, data=data)

            assert response.status_code == 201
            assert response.data.get("code") == "SUCCESS"
            assert response.data.get("message") == "نظرسنجی با موفقیت ساخته شد"


        assert response.data.get("message") == "نظرسنجی با موفقیت ساخته شد"

    def test_if_data_invalid_returns_400(self, api_client, superuser):

        api_client.force_authenticate(user=superuser)

        response = api_client.post(self.url, data={})

        assert response.status_code == 400


    def test_if_creator_not_authenticated_returns_401(self, api_client, superuser):
        file_path = os.path.join(BASE_DIR, "surveys", "tests", "example.json")

        with open(file_path) as f:
            data = {"data": f.read()}

        response = api_client.post(self.url, data=data)

        assert response.status_code == 401

    def test_if_not_allowed_user_returns_403(self, api_client, student, employee, personal):
        users = [student, employee, personal]
        for user in users:
            api_client.force_authenticate(user=user)

            response = api_client.post(self.url, data={})

            assert response.status_code == 403





