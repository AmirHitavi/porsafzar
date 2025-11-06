import pytest
from django.urls import reverse

from .factories import OneTimeLinkFactory, SurveyFactory


@pytest.mark.django_db
class TestOneTimeLinkAccessView:
    view_name = "one-time-link-access"

    def test_if_token_valid_returns_survey_and_form_uuid(self, api_client):
        survey = SurveyFactory()
        link = OneTimeLinkFactory(survey=survey)

        url = reverse(self.view_name, args=[link.token])

        response = api_client.get(url)

        assert response.status_code == 200

        assert response.data.get("survey_uuid") == str(survey.uuid)

    def test_if_token_invalid_returns_404(self, api_client):
        url = reverse(self.view_name, args=["invalid_token"])

        response = api_client.get(url)

        assert response.status_code == 404
