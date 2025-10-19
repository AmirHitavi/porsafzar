from rest_framework_nested.routers import DefaultRouter

from surveys.api.views import SurveyViewSet

router = DefaultRouter()

router.register("surveys", SurveyViewSet)

urlpatterns = router.urls
