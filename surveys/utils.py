import json

from django.db import transaction
from django.utils import timezone
from django_celery_beat.models import ClockedSchedule, PeriodicTask

from .models import SurveyFormSettings


def survey_settings_activation(settings: SurveyFormSettings):
    form = settings.form
    parent_survey = form.parent

    with transaction.atomic():
        if settings.is_active:
            # غیرفعال کردن همه تنظیمات فرم ها با پدر یکسان
            SurveyFormSettings.objects.filter(form__parent=parent_survey).exclude(
                pk=settings.pk
            ).update(is_active=False)

            parent_survey.active_version = form
            parent_survey.save()

        else:
            if parent_survey.active_version == form:
                parent_survey.active_version = None
                parent_survey.save()


def schedule_task(task_name, task_func, run_at, form_settings_pk):
    if run_at and run_at > timezone.now():
        with transaction.atomic():
            task_name = f"{task_name}_{task_func}_{form_settings_pk}"
            PeriodicTask.objects.filter(name=task_name).delete()

            clocked, _ = ClockedSchedule.objects.get_or_create(clocked_time=run_at)
            PeriodicTask.objects.create(
                name=task_name,
                task=task_func,
                clocked=clocked,
                one_off=True,
                args=json.dumps([form_settings_pk]),
            )
