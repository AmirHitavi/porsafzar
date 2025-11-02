from datetime import datetime

from celery import shared_task
from django.db import transaction
from django.utils.dateparse import parse_datetime

from .models import Answer, AnswerSet
from .utils import create_answer, update_answer


@shared_task
def handle_create_post_save_answer_set(answerset_pk: int):
    try:
        answerset = AnswerSet.objects.get(pk=answerset_pk)
        metadata = answerset.metadata

        with transaction.atomic():
            for question_name, answer_value in metadata.items():
                create_answer(
                    answer_set=answerset,
                    question_name=question_name,
                    answer_value=answer_value,
                )
    except AnswerSet.DoesNotExist:
        return


@shared_task
def handle_update_post_save_answer_set(answerset_pk: int):
    try:
        answerset = AnswerSet.objects.get(pk=answerset_pk)
        metadata = answerset.metadata

        with transaction.atomic():
            for question_name, answer_value in metadata.items():
                update_answer(answerset, question_name, answer_value)

    except AnswerSet.DoesNotExist:
        return


@shared_task
def handle_answerset_soft_delete(answerset_pk: int):
    try:
        answerset = AnswerSet.deleted_objects.get(pk=answerset_pk)
        delete_time = answerset.deleted_at

        with transaction.atomic():
            answers = Answer.active_objects.filter(answerset=answerset)
            answers.update(deleted_at=delete_time)

    except AnswerSet.DoesNotExist:
        return


@shared_task
def handle_answerset_restore_delete(answerset_pk: int, delete_time):
    try:
        answerset = AnswerSet.active_objects.get(pk=answerset_pk)

        if isinstance(delete_time, datetime):
            parsed_delete_time = delete_time
        else:
            parsed_delete_time = parse_datetime(delete_time)

        with transaction.atomic():
            answers = Answer.deleted_objects.filter(
                answerset=answerset, deleted_at=parsed_delete_time
            )
            answers.update(deleted_at=None)

    except AnswerSet.DoesNotExist:
        return
