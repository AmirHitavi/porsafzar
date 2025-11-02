from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from surveys.api.selectors import get_form_by_uuid

from ..models import AnswerSet


def get_all_answersets_for_form(survey_uuid: str, form_uuid: str) -> QuerySet:
    form = get_form_by_uuid(parent_uuid=survey_uuid, form_uuid=form_uuid)
    return AnswerSet.active_objects.filter(survey_form=form)


def get_all_deleted_answersets_for_form(survey_uuid: str, form_uuid: str) -> QuerySet:
    form = get_form_by_uuid(parent_uuid=survey_uuid, form_uuid=form_uuid)
    return AnswerSet.deleted_objects.filter(survey_form=form)


def get_answerset_by_uuid(uuid: str) -> AnswerSet:
    return get_object_or_404(AnswerSet, uuid=uuid)


def get_active_answeset_by_uuid(uuid: str) -> AnswerSet:
    return get_object_or_404(AnswerSet.active_objects, uuid=uuid)


def get_soft_deleted_answerset_by_uuid(uuid: str) -> AnswerSet:
    return get_object_or_404(AnswerSet.deleted_objects, uuid=uuid)
