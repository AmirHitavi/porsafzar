import factory
from faker import Faker as FactoryFaker

from accounts.tests.factories import UserFactory

from ..models import Survey, SurveyForm

faker = FactoryFaker()


class SurveyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Survey

    title = factory.LazyAttribute(lambda _: faker.sentence())
    created_by = factory.SubFactory(UserFactory, is_staff=True, is_superuser=True)
    is_prebuilt = False


class SurveyFormFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SurveyForm

    version = factory.sequence(lambda n: n + 1)
    description = factory.LazyAttribute(lambda _: faker.sentences(nb=2))
    metadata = factory.LazyAttribute(lambda _: {"title": faker.name()})
    parent = factory.SubFactory(SurveyFactory)
