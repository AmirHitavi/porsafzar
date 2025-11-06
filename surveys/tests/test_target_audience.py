import pytest
from django.urls import reverse

from ..models import TargetAudience
from .factories import TargetAudienceFactory


@pytest.mark.django_db
class TestTargetAudienceViewSet:
    list_view_name = "target-audience-list"
    detail_view_name = "target-audience-detail"

    def test_list_if_allowed_returns_200(
        self, api_client, superuser, management, professor
    ):
        allowed_users = [superuser, management, professor]
        TargetAudienceFactory.create_batch(5)

        for user in allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(reverse(self.list_view_name))

            assert response.status_code == 200
            assert len(response.data) == 5

    def test_list_if_not_allowed_returns_403(
        self, api_client, student, personal, employee
    ):
        not_allowed_users = [student, personal, employee]
        for user in not_allowed_users:
            api_client.force_authenticate(user=user)

            response = api_client.get(reverse(self.list_view_name))

            assert response.status_code == 403

    def test_create_if_allowed_returns_201(self, api_client, superuser):
        api_client.force_authenticate(user=superuser)

        data = {"name": "Engineering Faculty", "description": "Test group"}

        response = api_client.post(reverse(self.list_view_name), data=data)

        assert response.status_code == 201

    def test_create_if_not_allowed_returns_403(self, api_client, student):
        api_client.force_authenticate(user=student)

        data = {"name": "Test Group"}

        response = api_client.post(reverse(self.list_view_name), data=data)

        assert response.status_code == 403

    def test_patch_if_allowed_returns_200(self, api_client, management):
        audience = TargetAudienceFactory()

        api_client.force_authenticate(user=management)

        data = {"name": "Updated Audience"}

        response = api_client.patch(
            reverse(self.detail_view_name, args=[audience.id]), data=data
        )

        assert response.status_code == 200

        audience.refresh_from_db()

        assert audience.name == data["name"]

    def test_patch_if_not_allowed_returns_403(self, api_client, student):
        audience = TargetAudienceFactory()

        api_client.force_authenticate(user=student)

        response = api_client.patch(
            reverse(self.detail_view_name, args=[audience.id]), data={"name": "Hack"}
        )

        assert response.status_code == 403

    def test_delete_if_allowed_returns_204(self, api_client, management):
        audience = TargetAudienceFactory()

        api_client.force_authenticate(user=management)

        response = api_client.delete(reverse(self.detail_view_name, args=[audience.id]))

        assert response.status_code == 204

        assert not TargetAudience.objects.filter(id=audience.id).exists()

    def test_delete_if_not_allowed_returns_403(self, api_client, employee):
        audience = TargetAudienceFactory()

        api_client.force_authenticate(user=employee)

        response = api_client.delete(reverse(self.detail_view_name, args=[audience.id]))

        assert response.status_code == 403

    def test_if_phone_not_exists_returns_400(self, api_client, superuser):
        api_client.force_authenticate(user=superuser)

        data = {
            "name": "Faculty",
            "include_phone_numbers": ["09121234567"],
        }

        response = api_client.post(reverse(self.list_view_name), data=data)

        assert response.status_code == 400
        assert response.data["include_phone_numbers"]

        data = {
            "name": "Faculty",
            "exclude_phone_numbers": ["09121234567"],
        }

        response = api_client.post(reverse(self.list_view_name), data=data)

        assert response.status_code == 400
        assert response.data["exclude_phone_numbers"]

    def test_if_duplicate_in_both_lists_returns_400(
        self, api_client, superuser, normal_user
    ):

        api_client.force_authenticate(user=superuser)

        data = {
            "name": "Faculty A",
            "include_phone_numbers": [normal_user.phone_number],
            "exclude_phone_numbers": [normal_user.phone_number],
        }

        response = api_client.post(reverse(self.list_view_name), data=data)

        assert response.status_code == 400
        assert response.data.get("include_phone_numbers")

    def test_if_all_phones_exist_returns_201(
        self, api_client, superuser, student, personal
    ):

        api_client.force_authenticate(user=superuser)

        data = {
            "name": "Valid Audience",
            "include_phone_numbers": [student],
            "exclude_phone_numbers": [personal],
        }

        response = api_client.post(reverse(self.list_view_name), data=data)

        assert response.status_code == 201
        assert TargetAudience.objects.filter(name="Valid Audience").exists()
