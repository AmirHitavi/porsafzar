import factory
from faker import Faker as FactoryFaker

from accounts.tests.factories import UserFactory
from surveys.tests.factories import SurveyFormFactory

from ..models import AnswerSet

faker = FactoryFaker()


class AnswerSetFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = AnswerSet

    user = factory.SubFactory(UserFactory)
    survey_form = factory.SubFactory(SurveyFormFactory)
    metadata = factory.LazyAttribute(lambda _: {"title": faker.name()})
    deleted_at = None
