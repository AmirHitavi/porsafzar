from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

from submissions.models import AnswerSet
from surveys.models import SurveyForm

User = get_user_model()


def validate_form_is_active(form: SurveyForm):
    settings = form.settings
    now = timezone.now()

    if settings.start_date and settings.start_date > now:
        raise PermissionDenied(
            detail={
                "code": "FORM_NOT_STARTED",
                "message": _("پرسشنامه هنوز شروع نشده و امکان ثبت پاسخ وجود ندارد."),
            }
        )

    if settings.end_date and settings.end_date < now:
        raise PermissionDenied(
            detail={
                "code": "FORM_EXPIRED",
                "message": _("مهلت پاسخگویی به این پرسشنامه به پایان رسیده است."),
            }
        )

    # if not settings.is_active:
    #     raise PermissionDenied(
    #         detail={
    #             "code": "FORM_NOT_ACTIVE",
    #             "message": _("پرسشنامه غیرفعال است و امکان ثبت پاسخ وجود ندارد."),
    #         }
    #     )


def validate_user_submission_limit(form: SurveyForm, user: User | None = None):
    settings = form.settings
    max_response = settings.max_submissions_per_user

    if max_response:
        if not user:
            raise NotAuthenticated(
                detail={
                    "code": "USER_NOT_AUTHENTICATED",
                    "message": _("برای ارسال پاسخ باید وارد سیستم شوید."),
                }
            )

        count = AnswerSet.objects.filter(user=user, survey_form=form).count()

        if count >= max_response:
            raise PermissionDenied(
                detail={
                    "code": "TOO_MANY_SUBMISSIONS",
                    "message": _(
                        f"شما نمی‌توانید بیش از {max_response} پاسخ ارسال کنید."
                    ),
                }
            )


def validate_form_is_editable(form: SurveyForm):
    settings = form.settings

    if not settings.is_editable:
        raise PermissionDenied(
            detail={
                "code": "FORM_NOT_EDITABLE",
                "message": _("این پرسشنامه قابل ویرایش نیست."),
            }
        )


#
#
# def validate_answerset_belongs_to_form(form: SurveyForm, answer_set: AnswerSet):
#     if form != answer_set.survey_form:
#         raise ValidationError({"answer_set": _("این جواب متعلق به این فرم نیست.")})


def validate_user_in_target(users, user: User):
    if user not in users:
        raise PermissionDenied(
            detail={
                "code": "USER_NOT_IN_TARGET",
                "message": _("شما اجازه پاسخگویی به این پرسشنامه را ندارید."),
            }
        )
