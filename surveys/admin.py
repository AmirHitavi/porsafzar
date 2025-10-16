from django.contrib import admin

from .models import (
    OneTimeLink,
    Question,
    QuestionOptions,
    Survey,
    SurveyForm,
    SurveyFormSettings,
    TargetAudience,
)


@admin.register(OneTimeLink)
class OneTimeLinkAdmin(admin.ModelAdmin):
    pass


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    pass


@admin.register(QuestionOptions)
class QuestionOptionsAdmin(admin.ModelAdmin):
    pass


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    pass


@admin.register(SurveyForm)
class SurveyFormAdmin(admin.ModelAdmin):
    pass


@admin.register(SurveyFormSettings)
class SurveyFormSettingsAdmin(admin.ModelAdmin):
    pass


@admin.register(TargetAudience)
class TargetAudienceAdmin(admin.ModelAdmin):
    pass
