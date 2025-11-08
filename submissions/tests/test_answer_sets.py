import os
import uuid

import pytest
from django.urls import reverse
from django.utils import timezone

from config.env import BASE_DIR
from surveys.models import SurveyFormSettings, generate_secure_token
from surveys.tests.factories import (
    OneTimeLinkFactory,
    SurveyFactory,
    SurveyFormFactory,
    TargetAudienceFactory,
)

from ..models import AnswerSet
from .factories import AnswerSetFactory


@pytest.mark.django_db
class TestAnswerSetCreation:
    submission_view_name = "survey-submissions-list"

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
                reverse(self.submission_view_name, args=[survey.uuid]),
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
            reverse(self.submission_view_name, args=[survey.uuid]), data={}
        )

        assert response.status_code == 400

    def test_if_survey_not_exists_returns_404(self, api_client, superuser):
        survey_uuid = uuid.uuid4()

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey_uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 404

    def test_if_form_not_exists_returns_400(self, api_client, superuser):
        # Create a survey
        survey = SurveyFactory(created_by=superuser)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 404

    def test_if_form_soft_deleted_returns_404(self, api_client, superuser):
        survey = SurveyFactory(created_by=superuser)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 404

    def test_if_survey_form_not_active_returns_403(self, api_client):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=False, is_editable=True, form=form)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 404

    def test_if_survey_form_not_started_returns_403(self, api_client):
        form = SurveyFormFactory()
        SurveyFormSettings.objects.create(
            form=form,
            is_active=True,
            is_editable=True,
            start_date=timezone.make_aware(timezone.datetime(2099, 1, 1)),
        )

        response = api_client.post(
            reverse(self.submission_view_name, args=[form.parent.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["code"] == "FORM_NOT_STARTED"

    def test_if_survey_form_expired_returns_403(self, api_client):
        form = SurveyFormFactory()
        SurveyFormSettings.objects.create(
            form=form,
            is_active=True,
            is_editable=True,
            end_date=timezone.make_aware(timezone.datetime(2000, 1, 1)),
        )

        response = api_client.post(
            reverse(self.submission_view_name, args=[form.parent.uuid]),
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
            reverse(self.submission_view_name, args=[survey.uuid]),
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
            reverse(self.submission_view_name, args=[survey.uuid]),
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
                reverse(self.submission_view_name, args=[survey.uuid]),
                data={"metadata": {}},
                format="json",
            )

        assert response.status_code == 403
        assert response.data.get("code") == "TOO_MANY_SUBMISSIONS"

    def test_if_form_has_target_valid_data_returns_200(self, api_client, student):
        survey = SurveyFactory()
        target = TargetAudienceFactory(roles=[1])
        form = SurveyFormFactory(parent=survey, target=target)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        api_client.force_authenticate(user=student)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]),
            data={"metadata": {}},
            format="json",
        )
        assert response.status_code == 201

    def test_if_form_has_target_not_valid_user_returns_403(
        self, api_client, student, management
    ):

        survey = SurveyFactory()
        target = TargetAudienceFactory(include_phone_numbers=[management.phone_number])
        form = SurveyFormFactory(parent=survey, target=target)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        api_client.force_authenticate(user=student)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]),
            data={"metadata": {}},
            format="json",
        )
        assert response.status_code == 403

    def test_if_form_has_target_not_authenticated_users_returns_401(self, api_client):
        survey = SurveyFactory()
        target = TargetAudienceFactory()
        form = SurveyFormFactory(parent=survey, target=target)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        response = api_client.post(
            reverse(self.submission_view_name, args=[survey.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 401

    def test_if_one_time_link_valid_returns_200(self, api_client):
        survey = SurveyFactory()
        one_time_link = OneTimeLinkFactory(survey=survey)
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        url = reverse(self.submission_view_name, args=[survey.uuid])
        url = f"{url}?token={one_time_link.token}"

        response = api_client.post(url, data={"metadata": {}}, format="json")

        assert response.status_code == 201

    def test_if_one_time_link_used_returns_400(self, api_client):
        survey = SurveyFactory()
        one_time_link = OneTimeLinkFactory(survey=survey, is_used=True)
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        url = reverse(self.submission_view_name, args=[survey.uuid])
        url = f"{url}?token={one_time_link.token}"

        response = api_client.post(url, data={"metadata": {}}, format="json")

        assert response.status_code == 403
        assert response.data.get("code") == "LINK_USED"

    def test_if_one_time_link_not_exists_returns_400(self, api_client):
        survey = SurveyFactory()
        token = generate_secure_token()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        url = reverse(self.submission_view_name, args=[survey.uuid])
        url = f"{url}?token={token}"

        response = api_client.post(url, data={"metadata": {}}, format="json")

        assert response.status_code == 404

    def test_if_one_time_link_not_belongs_to_survey_returns_400(self, api_client):
        first_survey = SurveyFactory()
        one_time_link = OneTimeLinkFactory(survey=first_survey)

        second_survey = SurveyFactory()
        second_survey_form = SurveyFormFactory(parent=second_survey)
        SurveyFormSettings.objects.create(
            is_active=True, is_editable=True, form=second_survey_form
        )
        url = reverse(self.submission_view_name, args=[second_survey.uuid])
        url = f"{url}?token={one_time_link.token}"

        response = api_client.post(url, data={"metadata": {}}, format="json")

        assert response.status_code == 400
        assert response.data.get("code") == "TOKEN_NOT_FOR_SURVEY"


@pytest.mark.django_db
class TestAnswerSetUpdate:
    view_name = "survey-submissions-detail"

    def test_if_editable_form_owner_answer_set_valid_data_returns_200(
        self, api_client, normal_user
    ):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=True, is_editable=True, form=form)

        answer_set = AnswerSetFactory(user=normal_user, survey_form=form)

        api_client.force_authenticate(user=normal_user)

        response = api_client.patch(
            reverse(self.view_name, args=[survey.uuid, answer_set.uuid]),
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
            reverse(self.view_name, args=[survey.uuid, answer_set.uuid]),
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
            reverse(self.view_name, args=[survey.uuid, answer_set.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 403

    def test_if_survey_form_not_active_returns_404(self, api_client):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)
        SurveyFormSettings.objects.create(is_active=False, is_editable=True, form=form)
        answer_set = AnswerSetFactory(survey_form=form)

        api_client.force_authenticate(user=answer_set.user)

        response = api_client.patch(
            reverse(self.view_name, args=[survey.uuid, answer_set.uuid]),
            data={"metadata": {}},
            format="json",
        )

        assert response.status_code == 404
        assert response.data.get("message") == "هیچ نسخه فعالی برای این نظرسنجی یافت نشد."



@pytest.mark.django_db
class TestAnswerSetSoftDeleteOperations:
    soft_delete_view_name = "survey-submissions-detail"
    restore_delete_view_name = "survey-submissions-restore"
    archived_view_name = "survey-submissions-list-deleted"

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
                args=[survey.uuid, answer_set.uuid],
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
                args=[survey.uuid, answer_set_uuid],
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
                    args=[survey.uuid, answer_set.uuid],
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
                args=[survey.uuid, answer_set.uuid],
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
                args=[survey.uuid, answer_set_uuid],
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
                args=[survey.uuid, answer_set.uuid],
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
                args=[survey.uuid, answer_set.uuid],
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
                args=[survey.uuid, answer_set.uuid],
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
                args=[survey.uuid, answer_set.uuid],
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
                    args=[survey.uuid, answer_set.uuid],
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
                args=[survey.uuid, answer_set.uuid],
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
                args=[survey.uuid, answer_set_uuid],
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
                args=[survey.uuid, answer_set.uuid],
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
                reverse(self.archived_view_name, args=[survey.uuid])
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
                reverse(self.archived_view_name, args=[survey.uuid])
            )

            assert response.status_code == 403

    def test_archived_list_if_not_authenticated_returns_401(self, api_client):
        survey = SurveyFactory()
        form = SurveyFormFactory(parent=survey)

        response = api_client.get(reverse(self.archived_view_name, args=[survey.uuid]))

        assert response.status_code == 401

    def test_archived_list_if_survey_not_exists_returns_404(
        self, api_client, superuser
    ):
        survey_uuid = uuid.uuid4()
        form = SurveyFormFactory()

        api_client.force_authenticate(user=superuser)

        response = api_client.get(reverse(self.archived_view_name, args=[survey_uuid]))

        assert response.status_code == 404

    def test_archived_list_if_form_not_exists_returns_404(self, api_client, superuser):
        survey = SurveyFactory()

        api_client.force_authenticate(user=superuser)

        response = api_client.get(reverse(self.archived_view_name, args=[survey.uuid]))

        assert response.status_code == 404
        assert response.data.get("message") == "هیچ نسخه فعالی برای این نظرسنجی یافت نشد."
