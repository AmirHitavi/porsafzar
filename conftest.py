import pytest
from rest_framework.test import APIClient

from accounts.tests.factories import UserFactory
from accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def normal_user(db):
    return UserFactory()


@pytest.fixture
def superuser(db):
    return UserFactory(is_staff=True, is_superuser=True)

@pytest.fixture
def student(db):
    return UserFactory(role=User.UserRole.STUDENT)

@pytest.fixture
def employee(db):
    return UserFactory(role=User.UserRole.EMPLOYEE)

@pytest.fixture
def professor(db):
    return UserFactory(role=User.UserRole.PROFESSOR)

@pytest.fixture
def personal(db):
    return UserFactory(role=User.UserRole.PERSONAL)

@pytest.fixture
def management(db):
    return UserFactory(role=User.UserRole.MANAGEMENT)