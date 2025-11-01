from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import Survey, SurveyForm

User = get_user_model()


def create_survey(user: User, title: Optional[str] = None) -> Survey:
    return Survey.objects.create(created_by=user, title=title)


def create_survey_form(
    parent: Survey, json_data, version: int, description: str | None = None
) -> SurveyForm:
    return SurveyForm.objects.create(
        parent=parent, metadata=json_data, version=version, description=description
    )


def delete_survey(survey: Survey, user: User) -> None:
    if user.is_superuser:
        survey.delete()
    else:
        survey.deleted_at = timezone.now()
        survey.save(update_fields=["deleted_at"])


def restore_survey(survey: Survey) -> None:
    survey.deleted_at = None
    survey.save(update_fields=["deleted_at"])
