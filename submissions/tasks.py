from datetime import datetime

from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive, make_aware

from .api.selectors import get_charts_data
from .models import Answer, AnswerSet
from .utils import create_answer, update_answer


def _parse_datetime(dt):
    if isinstance(dt, datetime):
        parsed = dt
    else:
        parsed = parse_datetime(dt)
    if parsed and is_naive(parsed):
        parsed = make_aware(parsed)
    return parsed


@shared_task
def handle_create_post_save_answer_set(pk: int):
    try:
        answerset = AnswerSet.objects.get(pk=pk)
        metadata = answerset.metadata
        survey = answerset.survey_form.parent

        with transaction.atomic():
            for question_name, answer_value in metadata.items():
                create_answer(
                    answer_set=answerset,
                    question_name=question_name,
                    answer_value=answer_value,
                )

        if survey.is_live and survey.active_version:
            channel_layer = get_channel_layer()
            form = survey.active_version
            questions = list(
                form.questions.filter(is_live=True).values_list("name", flat=True)
            )
            async_to_sync(channel_layer.group_send)(
                f"live_{survey.uuid}",
                {
                    "type": "chart_update",
                    "data": get_charts_data(form, questions),
                },
            )

    except AnswerSet.DoesNotExist:
        return


@shared_task
def handle_update_post_save_answer_set(answerset_pk: int):
    try:
        answerset = AnswerSet.objects.get(pk=answerset_pk)
        metadata = answerset.metadata
        survey = answerset.survey_form.parent

        with transaction.atomic():
            for question_name, answer_value in metadata.items():
                update_answer(answerset, question_name, answer_value)

        if survey.is_live and survey.active_version:
            channel_layer = get_channel_layer()
            form = survey.active_version
            questions = list(
                form.questions.filter(is_live=True).values_list("name", flat=True)
            )
            async_to_sync(channel_layer.group_send)(
                f"live_{survey.uuid}",
                {
                    "type": "chart_update",
                    "data": get_charts_data(form, questions),
                },
            )

    except AnswerSet.DoesNotExist:
        return


@shared_task
def handle_answerset_soft_delete(answerset_pk: int):
    try:
        answerset = AnswerSet.deleted_objects.get(pk=answerset_pk)
        delete_time = answerset.deleted_at

        with transaction.atomic():
            answers = Answer.active_objects.filter(answer_set=answerset)
            answers.update(deleted_at=delete_time)

    except AnswerSet.DoesNotExist:
        return


@shared_task
def handle_answerset_restore_delete(answerset_pk: int, delete_time):
    try:
        answerset = AnswerSet.active_objects.get(pk=answerset_pk)
        parsed_delete_time = _parse_datetime(delete_time)

        with transaction.atomic():
            answers = Answer.deleted_objects.filter(
                answer_set=answerset, deleted_at=parsed_delete_time
            )
            answers.update(deleted_at=None)

    except AnswerSet.DoesNotExist:
        return
