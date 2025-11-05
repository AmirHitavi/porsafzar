from django.urls import path
from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter

from submissions.api.views import AnswerSetViewSet
from surveys.api.views import (
    OneTimeLinkAccessView,
    OneTimeLinkViewSet,
    SurveyFormSettingsViewSet,
    SurveyFormViewSet,
    SurveyViewSet,
    TargetAudienceViewSet,
)

router = DefaultRouter()

router.register("surveys", SurveyViewSet, basename="survey")
router.register("target-audiences", TargetAudienceViewSet, basename="target-audience")

surveys_router = NestedDefaultRouter(router, "surveys", lookup="survey")
surveys_router.register("forms", SurveyFormViewSet, basename="survey-forms")
surveys_router.register("submissions", AnswerSetViewSet, basename="survey-submissions")
surveys_router.register("links", OneTimeLinkViewSet, basename="survey-links")

survey_forms_router = NestedDefaultRouter(surveys_router, "forms", lookup="form")
survey_forms_router.register(
    "settings", SurveyFormSettingsViewSet, basename="survey-form-settings"
)

urlpatterns = router.urls + surveys_router.urls + survey_forms_router.urls

urlpatterns += [
    path("<str:token>/", OneTimeLinkAccessView.as_view(), name="one-time-link-access"),
]
