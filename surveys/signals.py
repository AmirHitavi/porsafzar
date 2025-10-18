from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SurveyForm, SurveyFormSettings
from .utils import schedule_task, survey_settings_activation


@receiver(post_save, sender=SurveyFormSettings)
def handle_active_survey_form(sender, instance: SurveyFormSettings, **kwargs):

    survey_settings_activation(instance)

    if instance.start_date:
        schedule_task(
            "activate_form",
            "surveys.tasks.activate_form",
            instance.start_date,
            instance.pk,
        )

    if instance.end_date:
        schedule_task(
            "deactivate_form",
            "surveys.tasks.deactivate_form",
            instance.end_date,
            instance.pk,
        )


@receiver(post_save, sender=SurveyForm)
def post_save_create_form_settings(sender, instance, created, **kwargs):
    if created:
        SurveyFormSettings.objects.create(form=instance, is_editable=False)
