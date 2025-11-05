from django.db import transaction
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
def post_save_create_form_settings(sender, instance: SurveyForm, created, **kwargs):
    if created:
        transaction.on_commit(lambda: handle_form_post_save.delay(instance.pk))


@receiver(pre_save, sender=Survey)
def pre_save_survey(sender, instance: Survey, **kwargs):
    if instance.pk:
        old = Survey.objects.filter(pk=instance.pk).only("deleted_at").first()
        if old:
            _old_deleted_at[instance.pk] = old.deleted_at


@receiver(pre_save, sender=SurveyForm)
def pre_save_survey_form(sender, instance: SurveyForm, **kwargs):
    if instance.pk:
        old = SurveyForm.objects.filter(pk=instance.pk).only("deleted_at").first()
        if old:
            _old_deleted_at[instance.pk] = old.deleted_at


@receiver(post_save, sender=Survey)
def post_save_survey_soft_delete(sender, instance: Survey, created, **kwargs):
    if created:
        return

    if instance.deleted_at:
        handle_survey_soft_delete.delay(instance.pk)
    else:
        delete_time = _old_deleted_at.pop(instance.pk, None)
        if delete_time:
            handle_survey_restore_delete.delay(instance.pk, delete_time.isoformat())


@receiver(post_save, sender=SurveyForm)
def post_save_form_soft_delete(sender, instance: SurveyForm, created, **kwargs):
    if created:
        return

    if instance.deleted_at:
        if instance.parent and instance.parent.active_version == instance:
            settings = instance.settings
            settings.is_active = False
            settings.save(update_fields=["is_active"])

        handle_form_soft_delete.delay(instance.pk)
    else:
        delete_time = _old_deleted_at.pop(instance.pk, None)
        if delete_time:
            handle_form_restore_delete.delay(instance.pk, delete_time.isoformat())
