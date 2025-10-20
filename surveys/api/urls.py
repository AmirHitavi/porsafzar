from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter

from surveys.api.views import SurveyFormSettings, SurveyFormViewSet, SurveyViewSet

router = DefaultRouter()

router.register("surveys", SurveyViewSet)

surveys_router = NestedDefaultRouter(router, "surveys", lookup="survey")
surveys_router.register("forms", SurveyFormViewSet, basename="survey-forms")

survey_forms = NestedDefaultRouter(surveys_router, "forms", lookup="form")
survey_forms.register("settings", SurveyFormSettings, basename="survey-form-settings")


urlpatterns = router.urls + surveys_router.urls + survey_forms.urls
