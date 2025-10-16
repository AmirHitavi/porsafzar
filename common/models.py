from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_("تاریخ ایجاد"), auto_now_add=True)

    class Meta:
        abstract = True


class BaseUpdateModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_("تاریخ ایجاد"), auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name=_("تاریخ بروزرسانی"), auto_now=True)

    class Meta:
        abstract = True
