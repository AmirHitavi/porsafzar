from django.db.models import QuerySet
from rest_framework.generics import get_object_or_404

from ..models import Survey, SurveyForm, SurveyFormSettings


def get_active_surveys():
    return Survey.active_objects.all()


def get_deleted_surveys():
    return Survey.deleted_objects.all()


def get_survey_by_uuid(uuid):
    return get_object_or_404(Survey, uuid=uuid)


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


def get_all_active_forms():
    return SurveyForm.active_objects.all()


def get_all_deleted_forms():
    return SurveyForm.deleted_objects.all()


def get_all_settings():
    return SurveyFormSettings.objects.all()
