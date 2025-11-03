from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from surveys.api.selectors import get_active_version_form

from ..models import AnswerSet
from .selectors import get_active_answeset_by_uuid
from .validators import (
    validate_form_is_active,
    validate_form_is_editable,
    validate_user_submission_limit,
)

User = get_user_model()


def create_answerset(
    *,
    user: User | None = None,
    survey_uuid: str,
    metadata: dict,
) -> AnswerSet:
    form = get_active_version_form(survey_uuid)
    validate_form_is_active(form)
    if user and isinstance(user, AnonymousUser):
        user = None
    validate_user_submission_limit(form, user)
    return AnswerSet.objects.create(user=user, survey_form=form, metadata=metadata)


def update_answerset(
    *,
    survey_uuid: str,
    answerset_uuid: str,
    metadata: dict,
) -> AnswerSet:
    form = get_active_version_form(survey_uuid)
    answer_set = get_active_answeset_by_uuid(answerset_uuid)

    validate_form_is_active(form)
    validate_form_is_editable(form)

    updated_metadata = answer_set.metadata
    updated_metadata.update(metadata)

    answer_set.metadata = updated_metadata
    answer_set.save(update_fields=["metadata"])

    return answer_set


def delete_answerset(answer_set: AnswerSet, user: User) -> None:
    if user.is_superuser or user.is_staff:
        answer_set.delete()
    else:
        answer_set.deleted_at = timezone.now()
        answer_set.save(update_fields=["deleted_at"])


def restore_answerset(answer_set: AnswerSet) -> None:
    answer_set.deleted_at = None
    answer_set.save(update_fields=["deleted_at"])
