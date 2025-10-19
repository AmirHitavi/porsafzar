from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.models import BaseModel

User = get_user_model()


class Survey(BaseModel):
    uuid = models.UUIDField(
        verbose_name=_("uuid"),
        default=uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    title = models.CharField(
        verbose_name=_("عنوان نظرسنجی"), max_length=255, null=True, blank=True
    )
    created_by = models.ForeignKey(
        User,
        verbose_name=_("کاربر سازنده"),
        on_delete=models.SET_NULL,
        null=True,  # TODO delete this lines
        blank=True,
        related_name="surveys",
        editable=False,
    )
    active_version = models.ForeignKey(
        "SurveyForm",
        verbose_name=_("نسخه فعال"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_version",
        db_index=True,
    )
    is_prebuilt = models.BooleanField(verbose_name=_("قالب نظرسنجی "), default=False)
    deleted_at = models.DateTimeField(
        verbose_name=_("تاریخ حدف"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("نظرسنجی")
        verbose_name_plural = _("نظرسنجی ها")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title if self.title else ""


class TargetAudience(BaseModel):
    name = models.CharField(
        verbose_name=_("نام جامعه هدف"), max_length=255, null=True, blank=True
    )
    description = models.CharField(
        verbose_name=_("توضیحات جامعه هدف"), max_length=255, null=True, blank=True
    )
    roles = ArrayField(
        models.PositiveSmallIntegerField(choices=User.UserRole.choices),
        verbose_name=_("نقش های مجاز"),
        blank=True,
        default=list,
        help_text=_("لیست نقش‌های مجاز برای دسترسی"),
    )
    include_phone_numbers = ArrayField(
        models.CharField(
            max_length=11, validators=[RegexValidator(regex=r"^09\d{9}$")]
        ),
        verbose_name=_("شماره‌های تلفن همراه مجاز"),
        blank=True,
        default=list,
        help_text=_("لیست شماره تلفن‌هایی که به جامعه هدف اضافه میشوند."),
    )
    exclude_phone_numbers = ArrayField(
        models.CharField(
            max_length=11, validators=[RegexValidator(regex=r"^09\d{9}$")]
        ),
        verbose_name=_("شماره‌های تلفن همراه غیر مجاز"),
        blank=True,
        default=list,
        help_text=_("لیست شماره تلفن‌هایی که از جامعه هدف حذف میشوند."),
    )

    class Meta:
        verbose_name = _("جامعه هدف")
        verbose_name_plural = _("جامعه های هدف")
        ordering = ["-created_at"]

    def clean(self):
        super().clean()

        include_phone_numbers_set = set(self.include_phone_numbers)
        exclude_phone_numbers_set = set(self.exclude_phone_numbers)

        common_phone_numbers = include_phone_numbers_set & exclude_phone_numbers_set

        if common_phone_numbers:
            raise ValidationError(
                _("شماره های %(numbers)s نمی توانند هم در لیست مجاز و غیر مجاز باشند")
                % {"numbers": ", ".join(common_phone_numbers)}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class SurveyForm(BaseModel):
    uuid = models.UUIDField(
        verbose_name=_("uuid"),
        default=uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    version = models.IntegerField(
        verbose_name=_("نسخه فرم"), validators=[MinValueValidator(1)]
    )
    description = models.CharField(
        verbose_name=_("توضیحات فرم"), max_length=255, null=True, blank=True
    )
    metadata = models.JSONField(verbose_name=_("داده فرم"))
    parent = models.ForeignKey(
        Survey,
        verbose_name=_("نظرسنجی"),
        on_delete=models.CASCADE,
        related_name="forms",
        db_index=True,
    )
    target = models.ForeignKey(
        TargetAudience,
        verbose_name=_("جامعه هدف فرم"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forms",
        db_index=True,
    )
    deleted_at = models.DateTimeField(
        verbose_name=_("تاریخ حدف"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("فرم نظرسنجی")
        verbose_name_plural = _("فرم های نظرسنجی")
        ordering = ["-version"]
        unique_together = ["parent", "version"]


class SurveyFormSettings(BaseModel):
    form = models.OneToOneField(
        SurveyForm,
        verbose_name=_("فرم نظرسنجی"),
        on_delete=models.CASCADE,
        related_name="settings",
        db_index=True,
    )
    is_active = models.BooleanField(
        verbose_name=_("فعال بودن"), default=True, db_index=True
    )
    start_date = models.DateTimeField(
        verbose_name=_("تاریخ شروع"), null=True, blank=True
    )
    end_date = models.DateTimeField(
        verbose_name=_("تاریخ پایان"), null=True, blank=True
    )
    max_submissions_per_user = models.PositiveSmallIntegerField(
        verbose_name=_("تعداد دفعات جواب دادن پرسشنامه توسط کاربر"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    is_editable = models.BooleanField(verbose_name=_("قابل ویرایش بودن جواب"))

    class Meta:
        verbose_name = _(" تنظمیات فرم نظرسنجی")
        verbose_name_plural = _("تنظیمات فرم های نظرسنجی")
        ordering = ["-created_at"]

    def clean(self):
        super().clean()

        now = timezone.now()

        errors = {}

        if self.start_date and self.end_date and self.start_date >= self.end_date:
            errors["end_date"] = _("تاریخ پایان نمی تواند بعد از تاریخ شروع باشد.")

        if self.start_date and self.start_date < now:
            errors["start_date"] = _("تاریخ شروع نمی‌تواند در گذشته باشد.")

        if self.end_date and self.end_date <= now:
            errors["end_date"] = _("تاریخ پایان باید بعد از زمان حال باشد.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class OneTimeLink(BaseModel):
    survey = models.ForeignKey(
        Survey,
        verbose_name=_("نظرسنجی"),
        on_delete=models.CASCADE,
        related_name="onetime_links",
        db_index=True,
    )
    token = models.CharField(
        verbose_name=_("token"), unique=True, default=uuid4, editable=False
    )
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("لینک یکبار مصرف")
        verbose_name_plural = _("لینک های یکبار مصرف")
        ordering = ["-created_at"]


class Question(BaseModel):

    class QuestionType(models.TextChoices):
        RADIOGROUP = "radiogroup", _("گزینه ای")
        RATING = "rating", _("امتیازی")
        SLIDER = "slider", _("اسلایدر")
        CHECKBOX = "checkbox", _("چند انتخابی")
        DROPDOWN = "dropdown", _("لیست کشویی")
        TAGBOX = "tagbox", _("جعبه تگ")
        BOOLEAN = "boolean", _("صحیح/غلط")
        FILE = "file", _("فایل")
        IMAGEPICKER = "imagepicker", _("انتخاب تصویر")
        RANKING = "ranking", _("رتبه بندی")
        TEXT = "text", _("متنی کوتاه")
        COMMENT = "comment", _("متنی بلند")
        MULTIPLETEXT = "multipletext", _("چند متنی")
        PANEL = "panel", _("پنل")
        PANELDYNAMIC = "paneldynamic", _("پنل پویا")
        MATRIX = "matrix", _("ماتریس")
        MATRIXDROPDOWN = "matrixdropdown", _("ماتریس کشویی")
        MATRIXDYNAMIC = "matrixdynamic", _("ماتریس پویا")
        HTML = "html", _("HTML")
        EXPRESSION = "expression", _("عبارت")
        IMAGE = "image", _("تصویر")
        SIGNATUREPAD = "signaturepad", _("امضا")

    survey = models.ForeignKey(
        SurveyForm,
        verbose_name=_("فرم نظرسنجی"),
        on_delete=models.CASCADE,
        related_name="questions",
        db_index=True,
    )
    name = models.CharField(
        verbose_name=_("اسم سوال"),
        max_length=255,
        help_text=_("نام سوال برای استفاده در پردازش داده ها"),
        db_index=True,
    )
    title = models.TextField(
        verbose_name=_("عنوان سوال"),
        null=True,
        blank=True,
        help_text=_("متن سوال که به کاربر نمایش داده می شود"),
    )
    type = models.CharField(
        verbose_name=_("دسته بندی سوال"), max_length=30, choices=QuestionType.choices
    )
    is_live = models.BooleanField(verbose_name=_("وضعیت زنده بودن"), default=False)
    parent = models.ForeignKey(
        "self",
        verbose_name=_("سوال پدر"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        verbose_name = _("سوال")
        verbose_name_plural = _("سوالات")
        ordering = ["-created_at"]
        unique_together = ["survey", "name"]

    def __str__(self):
        return f"{self.survey} ({self.name})"


class QuestionOptions(BaseModel):
    class OptionType(models.TextChoices):
        TEXT = "text", _("متنی")
        BOOLEAN = "boolean", _("بولین")
        NUMERIC = "numeric", _("عددی")
        IMAGE = "image", _("تصویر")
        JSON = "json", _("جیسون")

    question = models.ForeignKey(
        Question,
        verbose_name=_("سوال"),
        on_delete=models.CASCADE,
        related_name="options",
        db_index=True,
    )
    type = models.CharField(
        verbose_name=_("نوع گزینه"), choices=OptionType.choices, db_index=True
    )
    value = models.CharField(
        verbose_name=_("مقدار گزینه"),
        max_length=255,
        help_text=_("مقدار گزینه که در پردازش داده ها استفاده می شود"),
        db_index=True,
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
    image_value = models.ImageField(
        verbose_name=_("تصویر"),
        upload_to="surveys/options/images/",
        null=True,
        blank=True,
    )
    json_value = models.JSONField(verbose_name=_("مقدار JSON"), null=True, blank=True)

    class Meta:
        verbose_name = _("گزینه سوال")
        verbose_name_plural = _("گزینه های سوال")
        ordering = ["-created_at"]
        unique_together = ["question", "value"]

    def __str__(self):
        return f"گزینه {self.value} برای {self.question}"

    def clean(self):
        super().clean()

        field_mapping = {
            self.OptionType.TEXT: ("text_value", self.text_value),
            self.OptionType.BOOLEAN: ("boolean_value", self.boolean_value),
            self.OptionType.NUMERIC: ("numeric_value", self.numeric_value),
            self.OptionType.IMAGE: ("image_value", self.image_value),
            self.OptionType.JSON: ("json_value", self.json_value),
        }

        errors = {}

        # بررسی اینکه فیلد مربوط به نوع انتخاب شده پر شده باشد
        required_field_name, required_field_value = field_mapping.get(
            self.type, (None, None)
        )
        if required_field_value in [None, ""]:
            errors["type"] = _(
                f"برای نوع گزینه {self.get_type_display()} باید مقدار مربوطه پر شود"
            )

        # بررسی اینکه فیلدهای دیگر خالی باشند
        for field_type, (field_name, field_value) in field_mapping.items():
            if field_type != self.type and field_value not in [None, "", False]:
                errors[field_name] = _(
                    f"این فیلد فقط برای نوع گزینه '{self.OptionType(field_type).label}' قابل استفاده است"
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
