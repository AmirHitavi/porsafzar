import os
import uuid

import pytest
from django.urls import reverse
from django.utils import timezone

from config.env import BASE_DIR
from surveys.models import SurveyFormSettings
from surveys.tests.factories import SurveyFactory, SurveyFormFactory

from ..models import AnswerSet
from .factories import AnswerSetFactory


@pytest.mark.django_db
class TestAnswerSetCreation:
    create_url = reverse("survey-list")
    submission_view_name = "survey-form-submissions-list"

    def test_if_data_valid_returns_200(self, api_client, superuser, student):
        # Create a survey form
        survey_file_path = os.path.join(BASE_DIR, "submissions", "tests", "form.json")
        with open(survey_file_path) as survey_file:
            metadata = survey_file.read()

        survey = SurveyFactory(created_by=superuser)
        form = SurveyFormFactory(parent=survey, metadata=metadata)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

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
                reverse(self.submission_view_name, args=[survey.uuid, form.uuid]),
                data=data,
            )

            assert response.status_code == 201

    def test_if_data_invalid_returns_400(self, api_client, superuser):
        # Create a survey form
        survey_file_path = os.path.join(BASE_DIR, "submissions", "tests", "form.json")
        with open(survey_file_path) as survey_file:
            metadata = survey_file.read()

        survey = SurveyFactory(created_by=superuser)
        form = SurveyFormFactory(parent=survey, metadata=metadata)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        api_client.force_authenticate(user=None)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid, form.uuid]), data={}
        )

        assert response.status_code == 400

    def test_if_survey_not_exists_returns_404(self, api_client, superuser):
        # Create a survey form
        survey = SurveyFactory(created_by=superuser)
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        # delete survey
        survey_uuid = survey.uuid
        form_uuid = form.uuid
        survey.delete()

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey_uuid, form_uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 404

    def test_if_form_not_exists_returns_404(self, api_client, superuser):
        # Create a survey form
        survey = SurveyFactory(created_by=superuser)
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        # delete form
        survey_uuid = survey.uuid
        form_uuid = form.uuid
        form.delete()

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey_uuid, form_uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 404

    def test_if_form_soft_deleted_returns_404(self, api_client, superuser):
        survey = SurveyFactory(created_by=superuser)
        form = SurveyFormFactory(parent=survey, deleted_at=timezone.now())
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid, form.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 404

    def test_if_survey_form_not_active_returns_403(self, api_client):
        form = SurveyFormFactory()
        SurveyFormSettings.objects.create(is_active=False, is_editable=True, form=form)

        response = api_client.post(
            reverse(self.submission_view_name, args=[form.parent.uuid, form.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 403
        assert response.data.get("code") == "FORM_NOT_ACTIVE"

    def test_if_survey_form_not_started_returns_403(self, api_client):
        form = SurveyFormFactory()
        SurveyFormSettings.objects.create(
            form=form, is_active=True, is_editable=True, start_date="2099-01-01"
        )

        response = api_client.post(
            reverse(self.submission_view_name, args=[form.parent.uuid, form.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["code"] == "FORM_NOT_STARTED"

    def test_if_survey_form_expired_returns_403(self, api_client):
        form = SurveyFormFactory()
        SurveyFormSettings.objects.create(
            form=form, is_active=True, is_editable=True, end_date="2000-01-01"
        )

        response = api_client.post(
            reverse(self.submission_view_name, args=[form.parent.uuid, form.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["code"] == "FORM_EXPIRED"

    def test_if_survey_has_max_responses_per_user_valid_data_returns_201(
        self, api_client, normal_user
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(
            is_active=True, is_editable=True, form=form, max_submissions_per_user=1
        )

        api_client.force_authenticate(user=normal_user)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid, form.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 201

    def test_if_survey_has_max_responses_not_authenticated_users_returns_401(
        self, api_client
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(
            is_active=True, is_editable=True, form=form, max_submissions_per_user=1
        )

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid, form.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 401

    def test_if_survey_has_max_responses_user_max_limit_returns_403(
        self, api_client, normal_user
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        max_response = 1
        SurveyFormSettings.objects.create(
            is_active=True,
            is_editable=True,
            form=form,
            max_submissions_per_user=max_response,
        )

        for _ in range(max_response + 1):
            api_client.force_authenticate(user=normal_user)
            response = api_client.post(
                reverse(self.submission_view_name, args=[survey.uuid, form.uuid]),
                data={"metadata": {}},
                format="json",
            )

        assert response.status_code == 403
        assert response.data.get("code") == "TOO_MANY_SUBMISSIONS"


@pytest.mark.django_db
class TestAnswerSetUpdate:
    view_name = "survey-form-submissions-detail"

    def test_if_editable_form_owner_answer_set_valid_data_returns_200(
        self, api_client, normal_user
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        answer_set = AnswerSetFactory(user=normal_user, survey_form=form)

        api_client.force_authenticate(user=normal_user)

        response = api_client.patch(
            reverse(self.view_name, args=[survey.uuid, form.uuid, answer_set.uuid]),
            data={"metadata": {}},
            format="json",
        )
        assert response.status_code == 200

    def test_if_editable_form_not_owner_returns_403(
        self, api_client, normal_user, student
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form)

        api_client.force_authenticate(user=student)

        response = api_client.patch(
            reverse(self.view_name, args=[survey.uuid, form.uuid, answer_set.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 403

    def test_if_not_editable_returns_403(self, api_client, normal_user):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=False, form=form)
        answer_set = AnswerSetFactory(survey_form=form)

        api_client.force_authenticate(user=normal_user)

        response = api_client.patch(
            reverse(self.view_name, args=[survey.uuid, form.uuid, answer_set.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 403

    def test_if_survey_form_not_active_returns_403(self, api_client):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=False, is_editable=False, form=form)
        answer_set = AnswerSetFactory(survey_form=form)

        api_client.force_authenticate(user=answer_set.user)

        response = api_client.patch(
            reverse(self.view_name, args=[survey.uuid, form.uuid, answer_set.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestAnswerSetSoftDeleteOperations:
    soft_delete_view_name = "survey-form-submissions-detail"
    restore_delete_view_name = "survey-form-submissions-restore"
    archived_view_name = "survey-form-submissions-list-deleted"

    def test_soft_delete_if_owner_answer_set_exists_returns_200(
        self, api_client, management
    ):
        survey = SurveyFactory(created_by=management)
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form)

        api_client.force_authenticate(user=management)

        response = api_client.delete(
            reverse(
                self.soft_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set.uuid],
            )
        )
        assert response.status_code == 200

        answer_set.refresh_from_db()

        assert answer_set.deleted_at

    def test_soft_delete_if_admin_answer_set_exists_returns_200(
        self, api_client, superuser
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form)
        answer_set_uuid = answer_set.uuid

        api_client.force_authenticate(user=superuser)

        response = api_client.delete(
            reverse(
                self.soft_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set_uuid],
            )
        )

        assert response.status_code == 200

        assert AnswerSet.objects.filter(uuid=answer_set_uuid).exists() is False

    def test_soft_delete_if_not_allowed_users_answer_set_exists_returns_403(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form)

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.delete(
                reverse(
                    self.soft_delete_view_name,
                    args=[survey.uuid, form.uuid, answer_set.uuid],
                )
            )

            assert response.status_code == 403

    def test_soft_delete_if_not_authenticated_answer_set_exists_returns_401(
        self, api_client
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form)

        response = api_client.delete(
            reverse(
                self.soft_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set.uuid],
            )
        )

        assert response.status_code == 401

    def test_soft_delete_if_answer_set_not_exists_returns_404(
        self, api_client, superuser
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set_uuid = uuid.uuid4()

        api_client.force_authenticate(user=superuser)

        response = api_client.delete(
            reverse(
                self.soft_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set_uuid],
            )
        )
        assert response.status_code == 404

    def test_soft_delete_if_admin_answer_set_soft_deleted_returns_200(
        self, api_client, superuser
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form, deleted_at=timezone.now())

        api_client.force_authenticate(user=superuser)

        response = api_client.delete(
            reverse(
                self.soft_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set.uuid],
            )
        )

        assert response.status_code == 200

    def test_soft_delete_if_owner_answer_set_soft_deleted_returns_400(
        self, api_client, management
    ):
        survey = SurveyFactory(created_by=management)
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form, deleted_at=timezone.now())

        api_client.force_authenticate(user=survey.created_by)

        response = api_client.delete(
            reverse(
                self.soft_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set.uuid],
            )
        )

        assert response.status_code == 404

    def test_restore_delete_if_owner_answer_set_exists_returns_200(self, api_client):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form, deleted_at=timezone.now())

        api_client.force_authenticate(user=survey.created_by)

        response = api_client.post(
            reverse(
                self.restore_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set.uuid],
            ),
            data={},
        )

        assert response.status_code == 200

    def test_restore_delete_if_admin_answer_set_exists_returns_200(
        self, api_client, superuser
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form, deleted_at=timezone.now())

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(
                self.restore_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set.uuid],
            ),
            data={},
        )

        assert response.status_code == 200

    def test_restore_delete_if_not_allowed_users_answer_set_exists_returns_403(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form, deleted_at=timezone.now())

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.post(
                reverse(
                    self.restore_delete_view_name,
                    args=[survey.uuid, form.uuid, answer_set.uuid],
                ),
                data={},
            )
            assert response.status_code == 403

    def test_restore_delete_if_not_authenticated_answer_set_exists_returns_401(
        self, api_client
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form, deleted_at=timezone.now())

        response = api_client.post(
            reverse(
                self.restore_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set.uuid],
            ),
            data={},
        )

        assert response.status_code == 401

    def test_restore_delete_if_answer_set_not_exists_returns_404(
        self, api_client, superuser
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set_uuid = uuid.uuid4()

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(
                self.restore_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set_uuid],
            ),
            data={},
        )
        assert response.status_code == 404

    def test_restore_delete_if_answer_set_not_soft_deleted_returns_404(
        self, api_client, superuser
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form)

        api_client.force_authenticate(user=superuser)

        response = api_client.post(
            reverse(
                self.restore_delete_view_name,
                args=[survey.uuid, form.uuid, answer_set.uuid],
            ),
            data={},
        )

        assert response.status_code == 404

    def test_archived_if_allowed_users_exists_returns_200(self, api_client, superuser):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        AnswerSetFactory.create_batch(5, survey_form=form, deleted_at=timezone.now())
        AnswerSetFactory.create_batch(5, survey_form=form)

        allowed_users = [survey.created_by, superuser]
        for user in allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(
                reverse(self.archived_view_name, args=[survey.uuid, form.uuid])
            )

            assert response.status_code == 200
            assert len(response.data) == 5

    def test_archived_list_if_not_allowed_users_returns_403(
        self, api_client, student, employee, personal
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)
        AnswerSetFactory.create_batch(5, survey_form=form, deleted_at=timezone.now())

        not_allowed_users = [student, employee, personal]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(
                reverse(self.archived_view_name, args=[survey.uuid, form.uuid])
            )

            assert response.status_code == 403

    def test_archived_list_if_not_authenticated_returns_401(self, api_client):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)

        response = api_client.get(
            reverse(self.archived_view_name, args=[survey.uuid, form.uuid])
        )

        assert response.status_code == 401

    def test_archived_list_if_survey_not_exists_returns_404(
        self, api_client, superuser
    ):
        survey_uuid = uuid.uuid4()
        form = SurveyFormFactory()

        api_client.force_authenticate(user=superuser)

        response = api_client.get(
            reverse(self.archived_view_name, args=[survey_uuid, form.uuid])
        )

        assert response.status_code == 404

    def test_archived_list_if_form_not_exists_returns_404(self, api_client, superuser):
        survey = SurveyFactory()
        form_uuid = uuid.uuid4()

        api_client.force_authenticate(user=superuser)

        response = api_client.get(
            reverse(self.archived_view_name, args=[survey.uuid, form_uuid])
        )

        assert response.status_code == 404
