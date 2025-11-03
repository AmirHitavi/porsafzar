from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404

from ..models import Survey, SurveyForm, SurveyFormSettings


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
        raise ValidationError(_("هیچ نسخه فعالی برای این نظرسنجی یافت نشد."))
    return str(active_version.uuid)


def get_active_version_form(survey_uuid: str) -> SurveyForm:
    survey = get_survey_by_uuid(survey_uuid)
    active_version = survey.active_version
    if not active_version:
        raise ValidationError(
            {"message": _("هیچ نسخه فعالی برای این نظرسنجی یافت نشد.")}
        )
    return active_version
