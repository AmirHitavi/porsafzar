from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import ActiveObjectsManager, AllObjectsManager, DeletedObjectsManager


class BaseModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_("تاریخ ایجاد"), auto_now_add=True)

    class Meta:
        abstract = True


class BaseUpdateModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_("تاریخ ایجاد"), auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name=_("تاریخ بروزرسانی"), auto_now=True)

    class Meta:
        abstract = True


class SafeDeleteModel(models.Model):
    deleted_at = models.DateTimeField(
        verbose_name=_("تاریخ حدف"), null=True, blank=True
    )

    objects = AllObjectsManager()
    active_objects = ActiveObjectsManager()
    deleted_objects = DeletedObjectsManager()

    class Meta:
        abstract = True
