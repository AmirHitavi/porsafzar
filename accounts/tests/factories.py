import factory
from faker import Faker as FactoryFake

from ..models import User

faker = FactoryFake()


def generate_iranian_phone_number():
    return f"09{faker.random_number(digits=9, fix_len=True)}"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    phone_number = factory.LazyAttribute(lambda _: generate_iranian_phone_number())
    email = factory.LazyAttribute(lambda _: faker.email())
    role = factory.LazyAttribute(
        lambda _: faker.random_element(
            elements=[choice[0] for choice in User.UserRole.choices]
        )
    )
    birth_date = factory.LazyAttribute(lambda _: faker.date_of_birth(minimum_age=18))
    is_active = True
    is_staff = False
    is_superuser = False
