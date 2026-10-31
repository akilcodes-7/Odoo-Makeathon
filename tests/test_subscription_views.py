from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import Customer, Plan, Product, Subscription, SubscriptionLine


class SubscriptionWorkflowViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff@example.com", password="ValidPassword!", role=User.Role.STAFF)
        self.customer_user = User.objects.create_user("cust@example.com", password="ValidPassword!", role=User.Role.CUSTOMER)
        self.customer = Customer.objects.create(user=self.customer_user, display_name="Customer", billing_email=self.customer_user.email)
        self.product = Product.objects.create(name="Workspace", type=Product.Type.SOFTWARE, sales_price_paise=50_000, cost_price_paise=10_000)
        self.plan = Plan.objects.create(
            name="Workspace monthly", primary_product=self.product, price_paise=50_000,
            period=Plan.Period.MONTHLY, min_quantity=2, available_from=date(2020, 1, 1),
        )

    def valid_payload(self, **changes):
        today = timezone.localdate()
        payload = {
            "customer": self.customer.pk, "plan": self.plan.pk,
            "start_date": today.isoformat(), "expiry_date": (today + timedelta(days=60)).isoformat(),
            "quote_expires_on": (today + timedelta(days=21)).isoformat(),
            "payment_terms_days": "15", "lines-TOTAL_FORMS": "3", "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-product": str(self.product.pk), "lines-0-variant": "",
            "lines-0-is_primary": "on", "lines-0-quantity": "2", "lines-0-unit_price": "500.00",
            "lines-0-position": "0",
            "role": "ADMIN", "is_staff": "on",
        }
        payload.update(changes)
        return payload

    def test_staff_creates_quote_through_lifecycle_and_confirms_it(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse("subscriptions:new"), self.valid_payload())
        self.assertEqual(response.status_code, 302)
        subscription = Subscription.objects.get()
        self.assertEqual(subscription.status, Subscription.Status.DRAFT)
        self.assertEqual(subscription.lines.get().unit_price_paise, 50_000)
        self.assertFalse(subscription.created_by.is_superuser)

        response = self.client.post(reverse("subscriptions:action", args=[subscription.pk, "quote"]))
        self.assertEqual(response.status_code, 302)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.QUOTATION)
        self.assertEqual(subscription.quote_expires_on, timezone.localdate() + timedelta(days=21))

        self.client.post(reverse("subscriptions:action", args=[subscription.pk, "confirm"]))
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.CONFIRMED)
        self.assertEqual(subscription.billing_period, Plan.Period.MONTHLY)
        self.assertEqual(subscription.min_quantity_snapshot, 2)

    def test_manual_quote_expiry_is_visible_and_defaulted_on_draft_form(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("subscriptions:new"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="quote_expires_on"')
        self.assertContains(response, (timezone.localdate() + timedelta(days=7)).isoformat())

    def test_invalid_variant_and_wrong_primary_line_are_rejected(self):
        other = Product.objects.create(name="Extra", type=Product.Type.ADDON, sales_price_paise=1000, cost_price_paise=0)
        payload = self.valid_payload(**{"lines-0-product": str(other.pk)})
        self.client.force_login(self.staff)
        response = self.client.post(reverse("subscriptions:new"), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Subscription.objects.exists())
        self.assertContains(response, "primary line must match")

    def test_customer_cannot_access_internal_subscription_routes(self):
        self.client.force_login(self.customer_user)
        self.assertEqual(self.client.get(reverse("subscriptions:list")).status_code, 403)
        self.assertEqual(self.client.post(reverse("subscriptions:new"), {}).status_code, 403)

    def test_confirmed_terms_cannot_be_edited_from_view(self):
        subscription = Subscription.objects.create(
            number="SUB-EDIT", customer=self.customer, plan=self.plan,
            status=Subscription.Status.CONFIRMED, start_date=timezone.localdate(),
            expiry_date=timezone.localdate() + timedelta(days=60),
            billing_anchor_date=timezone.localdate(), billing_period=Plan.Period.MONTHLY,
        )
        SubscriptionLine.objects.create(subscription=subscription, product=self.product, is_primary=True, quantity=2, unit_price_paise=50_000)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("subscriptions:edit", args=[subscription.pk]))
        self.assertEqual(response.status_code, 302)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.CONFIRMED)
