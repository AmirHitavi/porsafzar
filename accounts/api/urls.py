from django.urls import path
from rest_framework_nested.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import UserViewSet

router = DefaultRouter()

router.register(r"users", UserViewSet)

urlpatterns = [
    path("jwt/refresh/", TokenRefreshView.as_view(), name="jwt_refresh"),
    path("jwt/verify/", TokenVerifyView.as_view(), name="jwt_verify"),
] + router.urls
