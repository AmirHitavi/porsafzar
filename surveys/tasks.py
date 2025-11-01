from datetime import datetime

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.generics import get_object_or_404

from submissions.models import Answer, AnswerSet

from .models import Survey, SurveyForm, SurveyFormSettings
from .utils import create_questions, survey_settings_activation


@shared_task
def handle_form_post_save(form_pk: int):
    form = SurveyForm.objects.get(pk=form_pk)
    with transaction.atomic():
        # create setting
        SurveyFormSettings.objects.create(form=form, is_editable=False)

        # create question
        form_json = form.metadata
        pages = form_json.get("pages", [])
        create_questions(form=form, pages=pages)


@shared_task
def handle_survey_soft_delete(survey_pk: int):
    try:
        survey = Survey.deleted_objects.get(pk=survey_pk)
        delete_time = survey.deleted_at

        with transaction.atomic():
            forms = SurveyForm.active_objects.filter(parent=survey)
            forms.update(deleted_at=delete_time)

            answer_sets = AnswerSet.active_objects.filter(survey_form__in=forms)
            answer_sets.update(deleted_at=delete_time)

            answers = Answer.active_objects.filter(answer_set__in=answer_sets)
            answers.update(deleted_at=delete_time)

    except Survey.DoesNotExist:
        return


@shared_task
def handle_survey_restore_delete(survey_pk: int, delete_time):
    try:
        survey = Survey.active_objects.get(pk=survey_pk)

        if isinstance(delete_time, datetime):
            parsed_delete_time = delete_time
        else:
            parsed_delete_time = parse_datetime(delete_time)

        with transaction.atomic():
            forms = SurveyForm.deleted_objects.filter(
                parent=survey, deleted_at=delete_time
            )
            forms.update(deleted_at=None)

            answer_sets = AnswerSet.deleted_objects.filter(
                survey_form__in=forms, deleted_at=delete_time
            )
            answer_sets.update(deleted_at=None)

            answers = Answer.deleted_objects.filter(
                answer_set__in=answer_sets, deleted_at=delete_time
            )
            answers.update(deleted_at=None)
    except Survey.DoesNotExist:
        return None


# @shared_task
# def handle_survey_form_soft_delete(form_pk: int):
#     try:
#         form = SurveyForm.deleted_objects.get(pk=form_pk)
#         delete_time = form.deleted_at
#
#         with transaction.atomic():
#             answer_sets = AnswerSet.active_objects.filter(survey_form=form)
#             answer_sets.update(deleted_at=delete_time)
#
#             answers = Answer.active_objects.filter(answer_set__in=answer_sets)
#             answers.update(deleted_at=delete_time)
#
#     except SurveyForm.DoesNotExist:
#         return
