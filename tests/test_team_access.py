from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class TeamAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin@example.com", password="ValidPassword!", role=User.Role.ADMIN)
        self.staff = User.objects.create_user("staff@example.com", password="ValidPassword!", role=User.Role.STAFF)
        self.customer = User.objects.create_user("customer@example.com", password="ValidPassword!", role=User.Role.CUSTOMER)

    def test_only_admin_can_create_staff(self):
        for user in (self.staff, self.customer):
            self.client.force_login(user)
            self.assertEqual(self.client.post(reverse("team:new"), {}).status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("team:new"), {
            "email": "new@example.com", "first_name": "New", "last_name": "Staff",
            "password1": "LongPassword!", "password2": "LongPassword!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.role, User.Role.STAFF)
        self.assertFalse(user.is_staff)
