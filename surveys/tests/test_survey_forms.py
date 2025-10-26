import os

import pytest
from django.urls import reverse
from django.utils import timezone

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


@pytest.mark.django_db
class TestSurveyFormSoftDeleteOperation:
    soft_delete_view_name = "survey-forms-soft-delete"
    revoke_delete_view_name = "survey-forms-revoke-delete"

    def test_soft_delete_if_admin_survey_form_exists_returns_200(
        self, api_client, superuser
    ):
        form = SurveyFormFactory()

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.soft_delete_view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "فرم حذف شد."

        form.refresh_from_db()
        assert form.deleted_at is not None

    def test_soft_delete_if_owner_survey_form_exists_returns_200(self, api_client):
        form = SurveyFormFactory()
        owner = form.parent.created_by

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.soft_delete_view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "فرم حذف شد."

        form.refresh_from_db()
        assert form.deleted_at is not None

    def test_soft_delete_if_not_allowed_user_survey_exists_returns_403(
        self, api_client, student, employee, personal
    ):
        form = SurveyFormFactory()

        not_allowed_users = [student, employee, personal]

        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.post(
                reverse(self.soft_delete_view_name, args=[form.parent.uuid, form.uuid]),
                data={},
            )

            assert response.status_code == 403

    def test_soft_delete_if_already_deleted_returns_400(self, api_client):
        form = SurveyFormFactory(deleted_at=timezone.now())
        owner = form.parent.created_by
        survey_uuid = form.parent.uuid
        form_uuid = form.uuid

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.soft_delete_view_name, args=[survey_uuid, form_uuid]), data={}
        )

        assert response.status_code == 400
        assert response.data.get("code") == "FORM_ALREADY_DELETED"
        assert response.data.get("message") == "فرم نظرسنجی قبلا حدف شده است"

    def test_soft_delete_if_form_not_exists_returns_404(self, api_client, superuser):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        form_uuid = form.uuid
        form.delete()

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.soft_delete_view_name, args=[survey_uuid, form_uuid]), data={}
        )

        assert response.status_code == 404
        assert response.data.get("code") == "FORM_DOES_NOT_EXIST"

    def test_soft_delete_if_user_not_authenticated_returns_401(self, api_client):
        form = SurveyFormFactory()

        response = api_client.post(
            reverse(self.soft_delete_view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 401

    def test_revoke_delete_if_admin_survey_form_exists_returns_200(
        self, api_client, superuser
    ):
        form = SurveyFormFactory(deleted_at=timezone.now())

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.revoke_delete_view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "فرم بازیابی شد."

    def test_revoke_delete_if_owner_survey_form_exists_returns_200(self, api_client):
        form = SurveyFormFactory(deleted_at=timezone.now())
        owner = form.parent.created_by

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.revoke_delete_view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "فرم بازیابی شد."

    def test_revoke_delete_if_not_allowed_user_survey_exists_returns_403(
        self, api_client, student, employee, personal
    ):
        form = SurveyFormFactory(deleted_at=timezone.now())

        not_allowed_users = [student, employee, personal]

        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.post(
                reverse(
                    self.revoke_delete_view_name, args=[form.parent.uuid, form.uuid]
                ),
                data={},
            )

            assert response.status_code == 403

    def test_revoke_delete_if_not_deleted_returns_400(self, api_client):
        form = SurveyFormFactory()
        owner = form.parent.created_by

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.revoke_delete_view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 400
        assert response.data.get("code") == "FORM_NOT_DELETED"

    def test_revoke_delete_if_form_not_exists_returns_404(self, api_client, superuser):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        form_uuid = form.uuid
        form.delete()

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.revoke_delete_view_name, args=[survey_uuid, form_uuid]),
            data={},
        )

        assert response.status_code == 404
        assert response.data.get("code") == "FORM_DOES_NOT_EXIST"

    def test_revoke_delete_if_user_not_authenticated_returns_401(self, api_client):
        form = SurveyFormFactory(deleted_at=timezone.now())

        response = api_client.post(
            reverse(self.soft_delete_view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 401


@pytest.mark.django_db
class TestSurveyFormActivation:
    view_name = "survey-forms-activate-form"

    def test_if_admin_form_not_active_returns_200(self, api_client, superuser):
        form = SurveyFormFactory()
        form.settings.is_active = False
        form.settings.save()

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "فرم فعال شد"

    def test_if_owner_form_not_active_returns_200(self, api_client):
        form = SurveyFormFactory()
        form.settings.is_active = False
        form.settings.save()
        owner = form.parent.created_by

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.view_name, args=[form.parent.uuid, form.uuid]),
            data={},
        )

        assert response.status_code == 200
        assert response.data.get("code") == "SUCCESS"
        assert response.data.get("message") == "فرم فعال شد"

    def test_if_form_active_returns_400(self, api_client):
        form = SurveyFormFactory()
        owner = form.parent.created_by

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.view_name, args=[form.parent.uuid, form.uuid]), data={}
        )

        assert response.status_code == 400
        assert response.data.get("code") == "FORM_ALREADY_ACTIVATED"

    def test_if_user_not_allowed_returns_403(
        self, api_client, student, employee, personal
    ):
        form = SurveyFormFactory()

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.post(
                reverse(self.view_name, args=[form.parent.uuid, form.uuid]), data={}
            )

            assert response.status_code == 403

    def test_if_user_not_authenticated_returns_401(self, api_client):
        form = SurveyFormFactory()

        response = api_client.post(
            reverse(self.view_name, args=[form.parent.uuid, form.uuid]), data={}
        )

        assert response.status_code == 401

    def test_if_form_not_exists_returns_404(self, api_client, superuser):
        form = SurveyFormFactory()
        survey_uuid = form.parent.uuid
        form_uuid = form.uuid
        form.delete()

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.view_name, args=[survey_uuid, form_uuid]), data={}
        )

        assert response.status_code == 404
        assert response.data.get("code") == "FORM_DOES_NOT_EXIST"

    def test_activate_second_form_deactivates_previous(self, api_client, superuser):
        survey = SurveyFactory()
        first_form = SurveyFormFactory(parent=survey)

        assert first_form.settings.is_active

        second_form = SurveyFormFactory(parent=survey)
        second_form.settings.is_active = False
        second_form.settings.save()

        assert second_form.settings.is_active is False

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.view_name, args=[survey.uuid, second_form.uuid]), data={}
        )

        assert response.status_code == 200

        survey.refresh_from_db()
        first_form.refresh_from_db()
        second_form.refresh_from_db()

        assert survey.active_version == second_form
        assert first_form.settings.is_active is False


@pytest.mark.django_db
class TestSurveyFormList:
    view_name = "survey-forms-list"

    def test_get_list_if_allowed_user_returns_200(
        self, api_client, superuser, professor, management
    ):
        survey = SurveyFactory()
        SurveyFormFactory.create_batch(10, parent=survey)

        allowed_users = [superuser, professor, management]

        for user in allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(reverse(self.view_name, args=[survey.uuid]))

            assert response.status_code == 200
            assert len(response.data) == 10

    def test_get_list_if_not_allowed_returns_401(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()
        SurveyFormFactory.create_batch(10, parent=survey)

        not_allowed_users = [student, employee, personal]

        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(reverse(self.view_name, args=[survey.uuid]))

            assert response.status_code == 403

    def test_get_list_if_user_not_authenticated_returns_401(self, api_client):
        survey = SurveyFactory()

        response = api_client.get(reverse(self.view_name, args=[survey.uuid]))

        assert response.status_code == 401
