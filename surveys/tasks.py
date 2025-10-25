from celery import shared_task
from django.db import transaction

from .models import SurveyFormSettings
from .utils import survey_settings_activation


@shared_task
def activate_form(form_settings_pk: int):
    with transaction.atomic():
        SurveyFormSettings.objects.filter(pk=form_settings_pk).update(is_active=True)

        settings = SurveyFormSettings.objects.get(pk=form_settings_pk)
        survey_settings_activation(settings)


@shared_task
def deactivate_form(form_settings_pk: int):
    with transaction.atomic():
        SurveyFormSettings.objects.filter(pk=form_settings_pk).update(is_active=False)

        settings = SurveyFormSettings.objects.get(pk=form_settings_pk)
        survey_settings_activation(settings)
