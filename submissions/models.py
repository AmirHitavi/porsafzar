from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import BaseUpdateModel, SafeDeleteModel
from surveys.models import Question, SurveyForm

User = get_user_model()


class AnswerSet(BaseUpdateModel, SafeDeleteModel):
    uuid = models.UUIDField(
        verbose_name=_("uuid"),
        default=uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    user = models.ForeignKey(
        User,
        verbose_name=_("کاربر"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="answer_sets",
    )
    survey_form = models.ForeignKey(
        SurveyForm,
        verbose_name=_("فرم پرسشنامه"),
        on_delete=models.CASCADE,
        related_name="answer_sets",
    )
    metadata = models.JSONField(verbose_name=_("جیسون جواب پرسشنامه"))

    class Meta:
        verbose_name = _("مجوعه جواب")
        verbose_name_plural = _("مجموعه های جواب")
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return f"answer set: {self.survey_form} form"


class Answer(BaseUpdateModel, SafeDeleteModel):
    class AnswerType(models.TextChoices):
        TEXT = "text", _("متنی")
        BOOLEAN = "boolean", _("بولین")
        NUMERIC = "numeric", _("عددی")
        FILE = "file", _("فایل")
        JSON = "json", _("جیسون")

    answer_set = models.ForeignKey(
        AnswerSet,
        verbose_name=_("مجموعه جواب"),
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        verbose_name=_("سوال"),
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question_type = models.CharField(verbose_name=_("نوع سوال"), max_length=30)
    answer_type = models.CharField(
        verbose_name=_("نوع جواب"), max_length=30, choices=AnswerType.choices
    )
    text_value = models.CharField(
        verbose_name=_("مقدار متنی"), max_length=255, null=True, blank=True
    )
    boolean_value = models.BooleanField(
        verbose_name=_("مقدار بولین"), null=True, blank=True
    )
    numeric_value = models.IntegerField(
        verbose_name=_("مقدار عددی"), null=True, blank=True
    )
    file_value = models.TextField(
        verbose_name=_("فایل"),
        null=True,
        blank=True,
    )
    json_value = models.JSONField(verbose_name=_("مقدار JSON"), null=True, blank=True)

    class Meta:
        verbose_name = _(" جواب")
        verbose_name_plural = _("جواب ها")
        unique_together = ("question", "answer_set")
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return f"answer {self.question.id} from {self.answer_set.id}"

    def clean(self):
        super().clean()

        fields_mapping = {
            self.AnswerType.TEXT: ("text_value", self.text_value),
            self.AnswerType.BOOLEAN: ("boolean_value", self.boolean_value),
            self.AnswerType.NUMERIC: ("numeric_value", self.numeric_value),
            self.AnswerType.FILE: ("file_value", self.file_value),
            self.AnswerType.JSON: ("json_value", self.json_value),
        }

        errors = {}

        required_field_name, required_field_value = fields_mapping[self.answer_type]

        #  بررسی اینکه فیلد مربوط به نوع انتخاب شده پر شده باشد
        if required_field_value is None:
            errors["answer_type"] = _(
                f"برای نو {self.get_answer_type_display()} باید مقدار مربوطه پرشود."
            )

        # # بررسی اینکه فیلدهای دیگر خالی باشند
        for field_type, (field_name, field_value) in fields_mapping.items():
            if field_type != self.answer_type and field_value is not None:
                errors[field_name] = _(
                    f"این فیلد فقط برای نوع گزینه {self.AnswerType(field_type).label}. قابل استفاده است"
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
