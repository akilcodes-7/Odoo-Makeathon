from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import Customer


class CustomerAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin@example.com", password="ValidPassword!", role=User.Role.ADMIN)
        self.staff = User.objects.create_user("staff@example.com", password="ValidPassword!", role=User.Role.STAFF)
        self.owner = User.objects.create_user("owner@example.com", password="ValidPassword!", role=User.Role.CUSTOMER)
        self.foreign = User.objects.create_user("foreign@example.com", password="ValidPassword!", role=User.Role.CUSTOMER)
        self.owned = Customer.objects.create(user=self.owner, display_name="Owner", billing_email=self.owner.email)
        self.other = Customer.objects.create(user=self.foreign, display_name="Other", billing_email=self.foreign.email)

    def test_staff_can_create_unlinked_customer_record(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("customers:new"), {
            "display_name": "Walk In", "billing_email": "walk@example.com", "phone": "",
            "billing_address": "", "is_active": "on", "user": self.owner.pk,
        })
        self.assertEqual(response.status_code, 302)
        customer = Customer.objects.get(billing_email="walk@example.com")
        self.assertIsNone(customer.user_id)

    def test_customer_cannot_edit_internal_customer_or_foreign_profile(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("customers:edit", args=[self.other.pk])).status_code, 403)
        response = self.client.get(reverse("customers:profile"))
        self.assertEqual(response.status_code, 200)

    def test_profile_post_ignores_user_link_and_internal_active_field(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("customers:profile"), {
            "display_name": "Updated Owner", "billing_email": "updated@example.com",
            "phone": "123", "billing_address": "Line 1", "user": self.foreign.pk, "is_active": "",
        })
        self.assertEqual(response.status_code, 302)
        self.owned.refresh_from_db()
        self.assertEqual(self.owned.display_name, "Updated Owner")
        self.assertEqual(self.owned.user_id, self.owner.pk)
        self.assertTrue(self.owned.is_active)

    def test_customer_list_is_internal_only(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("customers:list")).status_code, 403)

    def test_internal_customer_detail_is_role_protected(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("customers:detail", args=[self.owned.pk])).status_code, 200)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("customers:detail", args=[self.other.pk])).status_code, 403)
