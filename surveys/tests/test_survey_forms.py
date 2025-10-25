import json
import os

import pytest
from django.urls import reverse

from config.env import BASE_DIR

from .factories import SurveyFactory, SurveyFormFactory


@pytest.mark.django_db
class TestSurveyFormCreation:
    view_name = "survey-forms-list"

    def test_if_data_valid_returns_200(self, api_client, superuser):

        survey = SurveyFactory()

        file_path = os.path.join(BASE_DIR, "surveys", "tests", "example.json")

        with open(file_path, "r") as f:
            metadata = f.read()

        version = 1
        users = [survey.created_by, superuser]
        for user in users:
            version += 1

            data = {"version": version, "metadata": metadata, "description": ""}

            api_client.force_authenticate(user=user)

            response = api_client.post(
                reverse(self.view_name, args=[survey.uuid]), data=data
            )

            assert response.status_code == 201
            assert response.data.get("code") == "SUCCESS"
            assert response.data.get("message") == "فرم پرسشنامه بروزرسانی شد."

    def test_if_data_invalid_returns_400(self, api_client):
        survey = SurveyFactory()
        data = {}

        api_client.force_authenticate(user=survey.created_by)

        response = api_client.post(
            reverse(self.view_name, args=[survey.uuid]), data=data
        )

        assert response.status_code == 400

    def test_if_version_exists_returns_400(self, api_client):
        survey = SurveyFactory()
        SurveyFormFactory(parent=survey)

        file_path = os.path.join(BASE_DIR, "surveys", "tests", "example.json")

        with open(file_path, "r") as f:
            metadata = f.read()

        data = {"version": 1, "metadata": metadata, "description": ""}

        api_client.force_authenticate(user=survey.created_by)

        response = api_client.post(
            reverse(self.view_name, args=[survey.uuid]), data=data
        )

        assert response.status_code == 400
        assert response.data.get("code") == "FORM_VERSION_EXISTS"

    def test_if_user_not_authenticated_returns_401(self, api_client):
        survey = SurveyFactory()

        response = api_client.post(reverse(self.view_name, args=[survey.uuid]), data={})

        assert response.status_code == 401

    def test_if_not_allowed_user_returns_403(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.post(
                reverse(self.view_name, args=[survey.uuid]), data={}
            )

            assert response.status_code == 403
