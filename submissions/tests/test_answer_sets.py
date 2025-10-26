import os

import pytest
from django.urls import reverse

from config.env import BASE_DIR
from surveys.tests.factories import SurveyFactory, SurveyFormFactory


@pytest.mark.django_db(transaction=True)
class TestAnswerSetCreation:
    create_url = reverse("survey-list")
    submission_view_name = "survey-submissions-list"

    def test_if_data_valid_returns_200(self, api_client, superuser, student):
        # Create a survey form
        survey_file_path = os.path.join(BASE_DIR, "submissions", "tests", "form.json")

        with open(survey_file_path) as survey_file:
            data = {"data": survey_file.read()}

        api_client.force_authenticate(user=superuser)
        response = api_client.post(self.create_url, data)

        assert response.status_code == 201

        survey_uuid = response.data.get("data").get("survey_uuid")
        assert survey_uuid

        # create a answer set for the created survey
        submission_file_path = os.path.join(
            BASE_DIR, "submissions", "tests", "submit.json"
        )

        with open(submission_file_path) as submission_file:
            data = {"metadata": submission_file.read()}

        users = [None, superuser, student]
        for user in users:
            api_client.force_authenticate(user=user)

            response = api_client.post(
                reverse(self.submission_view_name, args=[survey_uuid]), data=data
            )

            assert response.status_code == 201

    def test_if_data_invalid_returns_400(self, api_client, superuser):
        # Create a survey form
        survey_file_path = os.path.join(BASE_DIR, "submissions", "tests", "form.json")

        with open(survey_file_path) as survey_file:
            data = {"data": survey_file.read()}

        api_client.force_authenticate(user=superuser)
        response = api_client.post(self.create_url, data)

        assert response.status_code == 201

        survey_uuid = response.data.get("data").get("survey_uuid")
        assert survey_uuid

        api_client.force_authenticate(user=None)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey_uuid]), data={}
        )

        assert response.status_code == 400

    def test_if_survey_not_exists_returns_404(self, api_client):
        survey = SurveyFactory()
        survey_uuid = survey.uuid
        survey.delete()

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey_uuid]), data={}
        )

        assert response.status_code == 404
        assert response.data.get("code") == "FORM_NOT_FOUND"

    def test_if_survey_form_not_active_returns_403(self, api_client):
        form = SurveyFormFactory()
        # deactivate the form
        settings = form.settings
        settings.is_active = False
        settings.save()

        # pass the deactivated form as active form pf tje survey
        survey = form.parent
        survey.active_version = form
        survey.save()

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]), data={}
        )

        assert response.status_code == 403
        assert response.data.get("code") == "FORM_NOT_ACTIVE"

    def test_if_survey_has_max_responses_per_user_valid_data_returns_201(
        self, api_client, normal_user
    ):
        form = SurveyFormFactory()

        settings = form.settings
        settings.max_responses_per_user = 1
        settings.save()

        survey = form.parent
        survey.active_version = form
        survey.save()

        api_client.force_authenticate(user=normal_user)
        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 201
        assert response.data.get("code") == "SUCCESS"

    def test_if_survey_has_max_responses_not_authenticated_users_returns_401(
        self, api_client
    ):
        form = SurveyFormFactory()

        settings = form.settings
        settings.max_submissions_per_user = 1
        settings.save()

        survey = form.parent
        survey.active_version = form
        survey.save()

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]), data={}
        )

        assert response.status_code == 401

    def test_if_survey_has_max_responses_user_max_limit_returns_403(
        self, api_client, normal_user
    ):
        form = SurveyFormFactory()

        settings = form.settings
        max_submissions_per_user = 3
        settings.max_submissions_per_user = max_submissions_per_user
        settings.save()

        survey = form.parent
        survey.active_version = form
        survey.save()

        for _ in range(max_submissions_per_user):
            api_client.force_authenticate(user=normal_user)
            response = api_client.post(
                reverse(self.submission_view_name, args=[survey.uuid]),
                data={"metadata": {}},
                format="json",
            )

        response.status_code == 403
        response.data.get("code") == "TOO_MANY_SUBMISSIONS"
