from math import isnan

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Survey, SurveyForm, SurveyFormSettings
from .tasks import (
    handle_form_post_save,
    handle_form_restore_delete,
    handle_form_soft_delete,
    handle_survey_restore_delete,
    handle_survey_soft_delete,
)
from .utils import survey_settings_activation

_old_deleted_at = {}


@receiver(post_save, sender=SurveyFormSettings)
def handle_active_survey_form(sender, instance: SurveyFormSettings, **kwargs):

    survey_settings_activation(instance)


@receiver(post_save, sender=SurveyForm)
def post_save_create_form_settings(sender, instance, created, **kwargs):
    if created:
        handle_form_post_save.delay(instance.pk)


@receiver(pre_save, sender=Survey)
def pre_save_survey_to_capture_delete_time(sender, instance, **kwargs):
    if instance.pk:
        old_instance = Survey.objects.filter(pk=instance.pk).first()
        if old_instance:
            _old_deleted_at[instance.pk] = old_instance.deleted_at


@receiver(post_save, sender=Survey)
def post_save_survey_soft_delete(sender, instance, created, **kwargs):
    if not created:
        if instance.deleted_at:
            handle_survey_soft_delete.delay(instance.pk)
        else:
            delete_time = _old_deleted_at[instance.pk]
            handle_survey_restore_delete.delay(instance.pk, delete_time)


@receiver(pre_save, sender=SurveyForm)
def pre_save_form_to_capture_delete_time(sender, instance: SurveyForm, **kwargs):
    if instance.pk:
        old_instance = SurveyForm.objects.filter(pk=instance.pk).first()
        if old_instance:
            _old_deleted_at[instance.pk] = old_instance.deleted_at


@receiver(post_save, sender=SurveyForm)
def post_save_form_soft_delete(sender, instance: SurveyForm, created, **kwargs):
    if not created:
        if instance.deleted_at:
            parent = instance.parent
            if parent.active_version == instance:
                settings = instance.settings
                settings.is_active = False
                settings.save(update_fields=["is_active"])

            handle_form_soft_delete.delay(instance.pk)
        else:
            delete_time = _old_deleted_at[instance.pk]
            handle_form_restore_delete(instance.pk, delete_time)
