from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import get_object_or_404

from ..models import OneTimeLink, Survey, SurveyForm, SurveyFormSettings, TargetAudience

User = get_user_model()


def get_active_surveys():
    return Survey.active_objects.all()


def get_deleted_surveys():
    return Survey.deleted_objects.all()


def get_survey_by_uuid(uuid):
    return get_object_or_404(Survey, uuid=uuid)


def get_active_survey_by_uuid(uuid):
    return get_object_or_404(Survey.active_objects, uuid=uuid)


def get_soft_deleted_survey_by_uuid(uuid):
    return get_object_or_404(Survey.deleted_objects, uuid=uuid)


def get_all_active_survey_forms() -> QuerySet[SurveyForm]:
    return SurveyForm.active_objects.all()


def get_all_deleted_survey_forms() -> QuerySet[SurveyForm]:
    return SurveyForm.deleted_objects.all()


def get_form_by_uuid(parent_uuid, form_uuid) -> SurveyForm:
    parent = get_survey_by_uuid(parent_uuid)

    return get_object_or_404(SurveyForm, parent=parent, uuid=form_uuid)


def get_soft_deleted_form_by_uuid(parent_uuid, form_uuid) -> SurveyForm:

    return get_object_or_404(
        SurveyForm.deleted_objects, parent__uuid=parent_uuid, uuid=form_uuid
    )


def get_active_survey_form_by_uuid(parent_uuid, form_uuid) -> SurveyForm:
    return get_object_or_404(
        SurveyForm.active_objects, parent__uuid=parent_uuid, uuid=form_uuid
    )


def get_all_active_forms():
    return SurveyForm.active_objects.all()


def get_all_deleted_forms():
    return SurveyForm.deleted_objects.all()


def get_all_settings():
    return SurveyFormSettings.objects.all()


def get_active_version_form_uuid(survey_uuid) -> str | None:
    survey = get_active_survey_by_uuid(survey_uuid)
    active_version = survey.active_version
    if not active_version:
        raise NotFound({"message": _("هیچ نسخه فعالی برای این نظرسنجی یافت نشد.")})
    return str(active_version.uuid)


def get_active_version_form(survey_uuid: str) -> SurveyForm:
    survey = get_survey_by_uuid(survey_uuid)
    active_version = survey.active_version
    if not active_version:
        raise NotFound({"message": _("هیچ نسخه فعالی برای این نظرسنجی یافت نشد.")})
    return active_version


def get_all_target_audiences() -> QuerySet[TargetAudience]:
    return TargetAudience.objects.all()


def get_all_users_target(target: TargetAudience) -> QuerySet[User]:

    roles = target.roles or []
    includes_user = target.include_phone_numbers or []
    excludes_user = target.exclude_phone_numbers or []

    query = Q()

    if roles:
        query |= Q(role__in=roles)

    if includes_user:
        query |= Q(phone_number__in=includes_user)

    users = User.objects.filter(query)

    if excludes_user:
        users = users.exclude(phone_number__in=excludes_user)

    return users.distinct()


def get_all_one_time_links(survey_uuid: str) -> QuerySet:
    survey = get_survey_by_uuid(survey_uuid)
    return OneTimeLink.objects.filter(survey=survey)


def get_one_time_link_by_token(token: str):
    token = token.rstrip("/").strip()
    return get_object_or_404(OneTimeLink, token=token)
