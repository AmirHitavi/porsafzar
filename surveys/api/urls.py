from rest_framework_nested.routers import DefaultRouter, NestedDefaultRouter

from surveys.api.views import SurveyFormViewSet, SurveyViewSet

router = DefaultRouter()

router.register("surveys", SurveyViewSet)

surveys_router = NestedDefaultRouter(router, "surveys", lookup="survey")
surveys_router.register("forms", SurveyFormViewSet, basename="survey-forms")


urlpatterns = router.urls + surveys_router.urls
