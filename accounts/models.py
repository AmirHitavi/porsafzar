from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.models import BaseUpdateModel


class UserManager(BaseUserManager):
    def create_user(self, phone_number, **extra_fields):
        """Create and save a new user with given phone number."""
        if not phone_number:
            raise ValueError(_("کاربر باید شماره تلفن داشته باشد."))

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password, **extra_fields):
        """Create and save a new superuser with given phone number."""
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_active") is False:
            raise ValueError(_("مدیر سامانه باید فعال باشد"))
        if extra_fields.get("is_staff") is False:
            raise ValueError(_("مدیر سامانه باید دسترسی کارمند داشته باشد."))
        if extra_fields.get("is_superuser") is False:
            raise ValueError(_("مدیر سامانه باید دسترسی ابرکاربر داشته باشد."))

        user = self.create_user(phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin, BaseUpdateModel):

    class UserRole(models.IntegerChoices):
        STUDENT = 1, _("دانشجو")
        EMPLOYEE = 2, _("کارمند")
        PROFESSOR = 3, _("استاد")
        PERSONAL = 4, _("خدمات")
        MANAGEMENT = 5, _("مدیریت")

    phone_number = models.CharField(
        verbose_name=_("تلفن همراه"),
        max_length=11,
        unique=True,
        help_text=_(
            "ضرروی است. شماره تلفن همراه معتبر شامل ۱۱ رقم به فرم ۰۹۱۹۱۲۳۴۵۶۷ می باشد"
        ),
        validators=[
            RegexValidator(
                regex=r"^09\d{9}$",
                message=_(
                    "شماره تلفن همراه معتبر ۱۱ رقم دارد و با ۰۹ شروع میشود.مانند ۰۹۱۹۱۲۳۴۵۶۷"
                ),
            )
        ],
        error_messages={
            "unique": _("کاربری با این شماره تلفن وجود دارد."),
        },
    )
    email = models.EmailField(
        verbose_name=_("ایمیل"), max_length=255, null=True, blank=True
    )
    role = models.PositiveSmallIntegerField(
        verbose_name=_("نقش"), choices=UserRole.choices, null=True, blank=True
    )
    birth_date = models.DateField(verbose_name=_("تاریخ تولد"), null=True, blank=True)

    is_active = models.BooleanField(verbose_name=_("فعال"), default=True)
    is_staff = models.BooleanField(verbose_name=_(" وضعیت ادمین سایت"), default=False)
    is_superuser = models.BooleanField(verbose_name=_("وضعیت مدیر سایت"), default=False)

    date_joined = models.DateTimeField(_("تاریخ عضویت"), default=timezone.now)
    last_login = models.DateTimeField(_("اخرین ورود"), blank=True, null=True)

    password = models.CharField(_("گذرواژه"), max_length=128, null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("کاربر")
        verbose_name_plural = _("کاربران")
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return self.phone_number

    def get_role_display(self):
        if self.role:
            return self.UserRole(self.role).label
        return _("تعریف نشده")
