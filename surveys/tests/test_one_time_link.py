import uuid

import pytest
from django.urls import reverse

from surveys.tests.factories import OneTimeLinkFactory, SurveyFactory


@pytest.mark.django_db
class TestOneTimeLink:
    view_name = "survey-links-list"

    def test_list_if_allowed_users_returns_200(self, api_client, superuser):
        survey = SurveyFactory()
        OneTimeLinkFactory.create_batch(10, survey=survey)

        allowed_users = [survey.created_by, superuser]
        for user in allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(reverse(self.view_name, args=[survey.uuid]))

            assert response.status_code == 200
            assert len(response.data) == 10

    def test_if_superuser_data_valid_returns_201(self, api_client, superuser):
        survey = SurveyFactory()

        data = {"numbers": 10}

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.view_name, args=[survey.uuid]), data=data
        )

        assert response.status_code == 201

        survey.refresh_from_db()

        assert survey.onetime_links.count() == 10

    def test_if_owner_data_valid_returns_201(self, api_client):
        survey = SurveyFactory()

        data = {"numbers": 10}

        api_client.force_authenticate(user=survey.created_by)

        response = api_client.post(
            reverse(self.view_name, args=[survey.uuid]), data=data
        )

        assert response.status_code == 201

        survey.refresh_from_db()

        assert survey.onetime_links.count() == 10

    def test_if_data_invalid_returns_400(self, api_client):
        survey = SurveyFactory()

        data = {"numbers": 0}

        api_client.force_authenticate(user=survey.created_by)

        response = api_client.post(
            reverse(self.view_name, args=[survey.uuid]), data=data
        )

        assert response.status_code == 400

    def test_if_survey_not_exists_returns_404(self, api_client, superuser):
        survey_uuid = uuid.uuid4()

        data = {"numbers": 10}

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.view_name, args=[survey_uuid]), data=data
        )

        assert response.status_code == 404

    def test_if_not_allowed_users_returns_403(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()

        data = {"numbers": 10}

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.post(
                reverse(self.view_name, args=[survey.uuid]), data=data
            )

            assert response.status_code == 403

    def test_if_not_authenticated_returns_401(self, api_client):
        survey = SurveyFactory()

        response = api_client.post(reverse(self.view_name, args=[survey.uuid]), data={})

        assert response.status_code == 401
