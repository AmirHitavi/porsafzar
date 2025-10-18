from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SurveyForm, SurveyFormSettings


@receiver(post_save, sender=SurveyFormSettings)
def handle_active_survey_form(sender, instance, **kwargs):
    form = instance.form
    parent_survey = form.parent

    with transaction.atomic():
        if instance.is_active is True:
            # غیرفعال کردن همه تنظیمات فرم ها با پدر یکسان
            SurveyFormSettings.objects.filter(form__parent=parent_survey).exclude(
                pk=instance.pk
            ).update(is_active=False)

            parent_survey.active_version = form
            parent_survey.save()

        else:
            if parent_survey.active_version == form:
                parent_survey.active_version = None
                parent_survey.save()


@receiver(post_save, sender=SurveyForm)
def post_save_create_form_settings(sender, instance, created, **kwargs):
    if created:
        SurveyFormSettings.objects.create(form=instance, is_editable=False)
