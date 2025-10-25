import pytest
from django.urls import reverse

from surveys.tests.factories import SurveyFormFactory


@pytest.mark.django_db(transaction=True)
class TestSurveyFormSettings:
    view_name = "survey-form-settings-detail"

    def test_get_if_allowed_users_returns_200(self, api_client, superuser):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        owner = form.parent.created_by
        form_uuid = form.uuid
        settings_id = form.settings.id

        allowed_users = [owner, superuser]
        for user in allowed_users:

            api_client.force_authenticate(user=user)

            response = api_client.get(
                reverse(self.view_name, args=[survey_uuid, form_uuid, settings_id])
            )

            assert response.status_code == 200

    def test_get_if_not_allowed_users_returns_403(
        self, api_client, student, employee, management
    ):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        form_uuid = form.uuid
        settings_id = form.settings.id

        not_allowed_users = [student, employee, management]

        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(
                reverse(self.view_name, args=[survey_uuid, form_uuid, settings_id])
            )

            assert response.status_code == 403

    def test_get_if_not_authenticated_returns_401(self, api_client):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        form_uuid = form.uuid
        settings_id = form.settings.id

        response = api_client.get(
            reverse(self.view_name, args=[survey_uuid, form_uuid, settings_id])
        )

        assert response.status_code == 401

    def test_patch_if_allowed_users_valid_data_returns_200(self, api_client, superuser):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        owner = form.parent.created_by
        form_uuid = form.uuid
        settings_id = form.settings.id

        allowed_users = [owner, superuser]

        data = {"is_active": True, "is_editable": True, "max_submissions_per_user": 2}

        for user in allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.patch(
                reverse(self.view_name, args=[survey_uuid, form_uuid, settings_id]),
                data=data,
            )

            assert response.status_code == 200

    def test_patch_if_allowed_users_invalid_data_returns_400(
        self, api_client, superuser
    ):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        owner = form.parent.created_by
        form_uuid = form.uuid
        settings_id = form.settings.id

        allowed_users = [owner, superuser]

        data = {"max_submissions_per_user": "invalid"}

        for user in allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.patch(
                reverse(self.view_name, args=[survey_uuid, form_uuid, settings_id]),
                data=data,
            )

            assert response.status_code == 400

    def test_patch_if_not_allowed_users_valid_data_returns_403(
        self, api_client, student, employee, management
    ):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        form_uuid = form.uuid
        settings_id = form.settings.id

        allowed_users = [student, employee, management]

        data = {"is_active": True, "is_editable": True, "max_submissions_per_user": 2}

        for user in allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.patch(
                reverse(self.view_name, args=[survey_uuid, form_uuid, settings_id]),
                data=data,
            )

            assert response.status_code == 403

    def test_patch_if_not_authenticated_returns_401(self, api_client, superuser):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        form_uuid = form.uuid
        settings_id = form.settings.id

        response = api_client.patch(
            reverse(self.view_name, args=[survey_uuid, form_uuid, settings_id]), data={}
        )

        assert response.status_code == 401
