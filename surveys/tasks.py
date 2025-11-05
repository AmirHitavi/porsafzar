from datetime import datetime

from celery import shared_task
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive, make_aware

from submissions.models import Answer, AnswerSet

from .models import Survey, SurveyForm, SurveyFormSettings
from .utils import create_questions


def _parse_datetime(dt):
    """Helper to safely parse datetime strings from Celery args."""
    if isinstance(dt, datetime):
        parsed = dt
    else:
        parsed = parse_datetime(dt)
    if parsed and is_naive(parsed):
        parsed = make_aware(parsed)
    return parsed


@shared_task
def handle_form_post_save(form_pk: int):
    try:
        form = SurveyForm.objects.get(pk=form_pk)
        with transaction.atomic():
            SurveyFormSettings.objects.create(form=form, is_editable=False)
            pages = form.metadata.get("pages", [])
            create_questions(form=form, pages=pages)
    except SurveyForm.DoesNotExist:
        return


@shared_task
def handle_survey_soft_delete(survey_pk: int):
    try:
        survey = Survey.deleted_objects.get(pk=survey_pk)
        delete_time = survey.deleted_at

        with transaction.atomic():
            forms = SurveyForm.active_objects.filter(parent=survey)
            forms_id = list(forms.values_list("id", flat=True))
            forms.update(deleted_at=delete_time)

            answer_sets = AnswerSet.active_objects.filter(survey_form_id__in=forms_id)
            answer_sets_id = list(answer_sets.values_list("id", flat=True))
            answer_sets.update(deleted_at=delete_time)

            answers = Answer.active_objects.filter(answer_set_id__in=answer_sets_id)
            answers.update(deleted_at=delete_time)

    except Survey.DoesNotExist:
        return


@shared_task
def handle_survey_restore_delete(survey_pk: int, delete_time):
    try:
        parsed_delete_time = _parse_datetime(delete_time)
        survey = Survey.active_objects.get(pk=survey_pk)

        with transaction.atomic():
            forms = SurveyForm.deleted_objects.filter(
                parent=survey, deleted_at=parsed_delete_time
            )
            forms_id = list(forms.values_list("id", flat=True))
            forms.update(deleted_at=None)

            answer_sets = AnswerSet.deleted_objects.filter(
                survey_form_id__in=forms_id, deleted_at=parsed_delete_time
            )
            answer_sets_id = list(answer_sets.values_list("id", flat=True))
            answer_sets.update(deleted_at=None)

            answers = Answer.deleted_objects.filter(
                answer_set_id__in=answer_sets_id, deleted_at=parsed_delete_time
            )
            answers.update(deleted_at=None)
    except Survey.DoesNotExist:
        return


@shared_task
def handle_form_soft_delete(form_pk: int):
    try:
        form = SurveyForm.deleted_objects.get(pk=form_pk)
        delete_time = form.deleted_at

        with transaction.atomic():
            answer_sets = AnswerSet.active_objects.filter(survey_form=form)
            answer_sets_id = list(answer_sets.values_list("id", flat=True))
            answer_sets.update(deleted_at=delete_time)

            answers = Answer.active_objects.filter(answer_set_id__in=answer_sets_id)
            answers.update(deleted_at=delete_time)

    except SurveyForm.DoesNotExist:
        return


@shared_task
def handle_form_restore_delete(form_pk: int, delete_time):
    try:
        parsed_delete_time = _parse_datetime(delete_time)
        form = SurveyForm.active_objects.get(pk=form_pk)

        with transaction.atomic():
            answer_sets = AnswerSet.deleted_objects.filter(
                survey_form=form, deleted_at=parsed_delete_time
            )
            answer_sets_id = list(answer_sets.values_list("id", flat=True))
            answer_sets.update(deleted_at=None)

            answers = Answer.deleted_objects.filter(
                answer_set_id__in=answer_sets_id, deleted_at=parsed_delete_time
            )
            answers.update(deleted_at=None)
    except SurveyForm.DoesNotExist:
        return
