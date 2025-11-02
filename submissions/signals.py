from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import AnswerSet
from .tasks import (
    handle_answerset_restore_delete,
    handle_answerset_soft_delete,
    handle_create_post_save_answer_set,
    handle_update_post_save_answer_set,
)

_old_deleted_at = {}


@receiver(post_save, sender=AnswerSet)
def post_save_answer_set(sender, instance, created, **kwargs):
    if created:
        handle_create_post_save_answer_set.delay(instance.pk)
    else:
        handle_update_post_save_answer_set.delay(instance.pk)


@receiver(pre_save, sender=AnswerSet)
def pre_save_answer_set_to_capture_delete_time(sender, instance, **kwargs):
    if instance.pk:
        old_instance = AnswerSet.objects.filter(pk=instance.pk).first()
        if old_instance:
            _old_deleted_at[old_instance] = old_instance.deleted_at


@receiver(post_save, sender=AnswerSet)
def post_save_answer_set_soft_delete(sender, instance, created, **kwargs):
    if not created:
        if instance.deleted_at:
            handle_answerset_soft_delete.delay(instance.pk)
        else:
            delete_time = _old_deleted_at.get(instance.pk)
            handle_answerset_restore_delete.delay(instance.pk, delete_time)
