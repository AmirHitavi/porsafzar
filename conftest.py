import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def normal_user(db):
    return UserFactory()


@pytest.fixture
def superuser(db):
    return UserFactory(is_staff=True, is_superuser=True)
