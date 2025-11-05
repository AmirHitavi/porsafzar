from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from ..models import OneTimeLink, Survey, SurveyForm
from .selectors import get_survey_by_uuid

User = get_user_model()


def create_survey(user: User, title: Optional[str] = None) -> Survey:
    return Survey.objects.create(created_by=user, title=title)


def create_survey_form(
    parent: Survey,
    json_data,
    version: int,
    description: str | None = None,
    target: int | None = None,
) -> SurveyForm:
    return SurveyForm.objects.create(
        parent=parent,
        metadata=json_data,
        version=version,
        description=description,
        target=target,
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


def activate_form(form: SurveyForm):
    settings = form.settings

    if settings.is_active:
        raise ValidationError({"message": _("فرم قبلا فعال شده است")})

    settings.is_active = True
    settings.save(update_fields=["is_active"])


def delete_form(form: SurveyForm, user: User):
    if user.is_superuser:
        form.delete()
    else:
        form.deleted_at = timezone.now()
        form.save(update_fields=["deleted_at"])


def restore_form(form: SurveyForm):
    form.deleted_at = None
    form.save(update_fields=["deleted_at"])


def generate_one_time_links(survey_uuid: str, number_of_links: int):
    survey = get_survey_by_uuid(survey_uuid)
    for i in range(number_of_links):
        OneTimeLink.objects.create(survey=survey)
