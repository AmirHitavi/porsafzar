from django.urls import path

from .consumers import SurveyLiveConsumer

websocket_urlpatterns = [
    path(r"api/v1/live/surveys/<uuid:survey_uuid>/", SurveyLiveConsumer.as_asgi()),
]
