import os
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from config.env import BASE_DIR

from ..models import Survey, SurveyForm
from ..tasks import handle_survey_restore_delete, handle_survey_soft_delete
from .factories import SurveyFactory, SurveyFormFactory


@pytest.mark.django_db
class TestSurveyCreation:
    url = reverse("survey-list")

    def test_if_data_valid_returns_200(
        self, api_client, superuser, professor, management
    ):
        file_path = os.path.join(BASE_DIR, "surveys", "tests", "example.json")

        with open(file_path) as f:
            data = {"data": f.read()}

        users = [superuser, professor, management]
        for user in users:
            api_client.force_authenticate(user=user)

            response = api_client.post(self.url, data=data)

            assert response.status_code == 201

            assert response.data == []

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

    def test_if_not_allowed_user_returns_403(
        self, api_client, student, employee, personal
    ):
        users = [student, employee, personal]
        for user in users:
            api_client.force_authenticate(user=user)

            response = api_client.post(self.url, data={})

            assert response.status_code == 403


@pytest.mark.django_db
class TestSurveySoftDeleteOperation:
    soft_delete_view_name = "survey-detail"
    restore_delete_view_name = "survey-restore"
    archived_list_view_name = "survey-list-deleted"
    archived_list_form_view_name = "survey-list-forms-deleted"

    def test_soft_delete_if_admin_survey_exists_returns_200(
        self, api_client, superuser
    ):
        survey = SurveyFactory()
        survey_uuid = survey.uuid
        forms = SurveyFormFactory.create_batch(5, parent=survey)
        forms_uuid = [form.uuid for form in forms]

        api_client.force_authenticate(user=superuser)

        response = api_client.delete(
            reverse(self.soft_delete_view_name, args=[survey_uuid])
        )

        assert response.status_code == 200

        assert Survey.objects.filter(uuid=survey_uuid).exists() is False

        for uuid in forms_uuid:
            assert SurveyForm.objects.filter(uuid=uuid).exists() is False

    @patch("surveys.signals.handle_survey_soft_delete.delay")
    def test_soft_delete_if_owner_survey_exists_returns_200(
        self, mock_delay, api_client, management
    ):
        survey = SurveyFactory(created_by=management)
        forms = SurveyFormFactory.create_batch(5, parent=survey)

        api_client.force_authenticate(user=management)

        response = api_client.delete(
            reverse(self.soft_delete_view_name, args=[survey.uuid])
        )

        handle_survey_soft_delete(survey.pk)

        assert response.status_code == 200

        survey.refresh_from_db()

        assert survey.deleted_at is not None

        for form in forms:
            form.refresh_from_db()
            assert form.deleted_at is not None
            assert form.deleted_at == survey.deleted_at

    def test_soft_delete_if_not_allowed_user_survey_exists_returns_403(
        self, api_client, normal_user
    ):
        surveys = SurveyFactory()

        api_client.force_authenticate(user=normal_user)

        response = api_client.delete(
            reverse(self.soft_delete_view_name, args=[surveys.uuid]), data={}
        )

        assert response.status_code == 403

    def test_soft_delete_if_already_deleted_returns_404(self, api_client):
        survey = SurveyFactory(deleted_at=timezone.now())
        owner = survey.created_by

        api_client.force_authenticate(user=owner)

        response = api_client.delete(
            reverse(self.soft_delete_view_name, args=[survey.uuid]), data={}
        )

        assert response.status_code == 404

    def test_soft_delete_if_not_exists_returns_404(self, api_client, superuser):
        survey = SurveyFactory()
        survey_uuid = survey.uuid
        survey.delete()

        api_client.force_authenticate(user=superuser)

        response = api_client.delete(
            reverse(self.soft_delete_view_name, args=[survey_uuid]), data={}
        )

        assert response.status_code == 404

    @patch("surveys.signals.handle_survey_restore_delete.delay")
    def test_restore_delete_if_admin_survey_exists_returns_200(
        self, mock_delay, api_client, superuser
    ):
        deleted_time = timezone.now()
        survey = SurveyFactory(deleted_at=deleted_time)
        forms = SurveyFormFactory.create_batch(
            5, parent=survey, deleted_at=deleted_time
        )

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(self.restore_delete_view_name, args=[survey.uuid]), data={}
        )

        assert response.status_code == 200

        handle_survey_restore_delete(survey.pk, deleted_time)

        survey.refresh_from_db()
        assert survey.deleted_at is None

        for form in forms:
            form.refresh_from_db()
            assert form.deleted_at is None

    def test_restore_delete_if_owner_survey_exists_returns_200(self, api_client):
        survey = SurveyFactory(deleted_at=timezone.now())
        owner = survey.created_by

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.restore_delete_view_name, args=[survey.uuid]), data={}
        )

        assert response.status_code == 200

        survey.refresh_from_db()

        assert survey.deleted_at is None

    def test_restore_delete_if_not_allowed_user_returns_403(
        self, api_client, normal_user
    ):
        surveys = SurveyFactory(deleted_at=timezone.now())

        api_client.force_authenticate(user=normal_user)

        response = api_client.post(
            reverse(self.restore_delete_view_name, args=[surveys.uuid]), data={}
        )

        assert response.status_code == 403

    def test_restore_delete_if_not_deleted_returns_404(self, api_client):
        survey = SurveyFactory()
        owner = survey.created_by

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.restore_delete_view_name, args=[survey.uuid]), data={}
        )

        assert response.status_code == 404

    def test_restore_delete_if_not_exists_returns_404(self, api_client):
        survey = SurveyFactory(deleted_at=timezone.now())
        survey_uuid = survey.uuid
        owner = survey.created_by
        survey.delete()

        api_client.force_authenticate(user=owner)

        response = api_client.post(
            reverse(self.restore_delete_view_name, args=[survey_uuid]), data={}
        )

        assert response.status_code == 404

    def test_archived_list_if_exists_returns_200(self, api_client, superuser):
        SurveyFactory.create_batch(3, deleted_at=timezone.now())

        api_client.force_authenticate(user=superuser)

        response = api_client.get(reverse(self.archived_list_view_name))

        assert response.status_code == 200
        assert len(response.data) == 3

    def test_archived_list_if_not_exists_returns_200(self, api_client, superuser):

        api_client.force_authenticate(user=superuser)

        response = api_client.get(reverse(self.archived_list_view_name))

        assert response.status_code == 200
        assert len(response.data) == 0

    def test_archived_list_if_not_allowed_user_returns_403(
        self, api_client, student, employee, personal
    ):
        SurveyFactory.create_batch(5, deleted_at=timezone.now())

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(reverse(self.archived_list_view_name))

            assert response.status_code == 403

    def test_archived_list_forms_if_exists_returns_200(self, api_client, superuser):
        survey = SurveyFactory()
        SurveyFormFactory.create_batch(5, parent=survey, deleted_at=timezone.now())

        api_client.force_authenticate(user=superuser)

        response = api_client.get(
            reverse(self.archived_list_form_view_name, args=[survey.uuid])
        )

        assert response.status_code == 200
        assert len(response.data) == 5

    def test_archived_list_forms_if_no_forms_returns_200(self, api_client):
        survey = SurveyFactory()

        api_client.force_authenticate(user=survey.created_by)

        response = api_client.get(
            reverse(self.archived_list_form_view_name, args=[survey.uuid])
        )

        assert response.status_code == 200
        assert len(response.data) == 0

    def test_archived_list_forms_if_not_allowed_user_returns_403(
        self, api_client, normal_user
    ):
        survey = SurveyFactory()
        SurveyFormFactory.create_batch(5, deleted_at=timezone.now())

        api_client.force_authenticate(user=normal_user)

        response = api_client.get(
            reverse(self.archived_list_form_view_name, args=[survey.uuid])
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestSurveyList:
    list_view_name = "survey-list"

    def test_if_authenticated_returns_200(self, api_client, normal_user):
        SurveyFactory.create_batch(10)
        SurveyFactory.create_batch(10, deleted_at=timezone.now())

        api_client.force_authenticate(user=normal_user)

        response = api_client.get(reverse(self.list_view_name))

        assert response.status_code == 200
        assert len(response.data) == 10

    def test_if_not_authenticated_returns_401(self, api_client):
        SurveyFactory.create_batch(10)

        response = api_client.get(reverse(self.list_view_name))

        assert response.status_code == 401


@pytest.mark.django_db
class TestSurveyDetail:
    view_name = "survey-detail"

    def test_get_if_allowed_users_form_exists_returns_200(self, api_client, superuser):
        survey = SurveyFactory()

        allowed_users = [survey.created_by, superuser]
        for user in allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(reverse(self.view_name, args=[survey.uuid]))

            assert response.status_code == 200
            assert response.data

    def test_get_if_not_allowed_users_form_exists_returns_403(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(reverse(self.view_name, args=[survey.uuid]))

            assert response.status_code == 403

    def test_get_if_form_not_exists_returns_404(self, api_client, superuser):
        survey = SurveyFactory()
        survey_uuid = survey.uuid
        survey.delete()

        api_client.force_authenticate(user=superuser)

        response = api_client.get(reverse(self.view_name, args=[survey_uuid]))

        assert response.status_code == 404

    def test_delete_if_owner_form_exists_returns_200(self, api_client):
        survey = SurveyFactory()

        api_client.force_authenticate(user=survey.created_by)

        response = api_client.delete(reverse(self.view_name, args=[survey.uuid]))

        assert response.status_code == 200

    def test_delete_if_admin_form_exists_returns_200(self, api_client, superuser):
        survey = SurveyFactory()

        api_client.force_authenticate(user=superuser)

        response = api_client.delete(reverse(self.view_name, args=[survey.uuid]))

        assert response.status_code == 200

    def test_delete_if_not_allowed_users_form_exists_returns_403(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.delete(reverse(self.view_name, args=[survey.uuid]))

            assert response.status_code == 403

    def test_delete_if_form_not_exists_returns_404(self, api_client, superuser):
        survey = SurveyFactory()
        survey_uuid = survey.uuid
        survey.delete()

        api_client.force_authenticate(user=superuser)

        response = api_client.delete(reverse(self.view_name, args=[survey_uuid]))

        assert response.status_code == 404

    def test_patch_if_data_valid_form_exists_returns_200(self, api_client, superuser):
        survey = SurveyFactory()

        allowed_users = [survey.created_by, superuser]
        for user in allowed_users:
            api_client.force_authenticate(user=user)

            data = {"title": f"update title by {user.phone_number}"}

            response = api_client.patch(
                reverse(self.view_name, args=[survey.uuid]), data=data
            )

            assert response.status_code == 200
            assert response.data["title"] == data["title"]

    def test_patch_if_not_allowed_users_data_valid_form_exists_returns_403(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            data = {}
            response = api_client.patch(
                reverse(self.view_name, args=[survey.uuid]), data=data
            )

            assert response.status_code == 403

    def test_patch_if_form_not_exists_returns_404(self, api_client, superuser):
        survey = SurveyFactory()
        survey_uuid = survey.uuid
        survey.delete()

        api_client.force_authenticate(user=superuser)

        response = api_client.patch(reverse(self.view_name, args=[survey_uuid]))

        assert response.status_code == 404

    def test_if_not_authenticated_returns_401(self, api_client):
        survey = SurveyFactory()

        response = api_client.get(reverse(self.view_name, args=[survey.uuid]))
        assert response.status_code == 401

        response = api_client.patch(reverse(self.view_name, args=[survey.uuid]))
        assert response.status_code == 401

        response = api_client.delete(reverse(self.view_name, args=[survey.uuid]))
        assert response.status_code == 401
