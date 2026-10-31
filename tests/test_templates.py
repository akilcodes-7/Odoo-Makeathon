from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import Customer, Plan, Product, QuoteTemplate, QuoteTemplateLine, Subscription
from offers.services.templates import copy_template_to_subscription


class QuoteTemplateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("template-admin@example.test", "ValidPassword!", role=User.Role.ADMIN)
        self.staff = User.objects.create_user("template-staff@example.test", "ValidPassword!", role=User.Role.STAFF)
        self.customer_user = User.objects.create_user("template-customer@example.test", "ValidPassword!", role=User.Role.CUSTOMER)
        self.customer = Customer.objects.create(user=self.customer_user, display_name="Customer", billing_email=self.customer_user.email)
        self.product = Product.objects.create(name="Workspace", type=Product.Type.SOFTWARE, sales_price_paise=40_000, cost_price_paise=10_000)
        self.addon = Product.objects.create(name="Support", type=Product.Type.ADDON, sales_price_paise=5_000, cost_price_paise=1_000)
        self.plan = Plan.objects.create(name="Monthly", primary_product=self.product, price_paise=40_000, period=Plan.Period.MONTHLY, min_quantity=2, available_from=date(2020, 1, 1))
        self.template = QuoteTemplate.objects.create(name="Standard", plan=self.plan, validity_days=14, created_by=self.admin)
        self.primary = QuoteTemplateLine.objects.create(template=self.template, product=self.product, is_primary=True, quantity=2, unit_price_paise=38_000, position=0)
        self.extra = QuoteTemplateLine.objects.create(template=self.template, product=self.addon, quantity=1, unit_price_paise=4_500, position=1)
        self.today = timezone.localdate()

    def make_draft(self, number="SUB-TEMPLATE"):
        return Subscription.objects.create(
            number=number, customer=self.customer, plan=self.plan,
            start_date=self.today, expiry_date=self.today + timedelta(days=60),
            billing_anchor_date=self.today, billing_period=self.plan.period,
        )

    def test_copy_snapshots_lines_and_source_edits_do_not_change_draft(self):
        draft = self.make_draft()
        draft = copy_template_to_subscription(self.template, draft)
        rows = list(draft.lines.order_by("position"))
        self.assertEqual([(row.product_id, row.quantity, row.unit_price_paise) for row in rows], [
            (self.product.pk, 2, 38_000), (self.addon.pk, 1, 4_500),
        ])
        self.assertEqual(draft.source_template_id, self.template.pk)
        self.primary.unit_price_paise = 90_000
        self.primary.save()
        self.assertEqual(draft.lines.get(is_primary=True).unit_price_paise, 38_000)

    def test_copy_rejects_different_plan_and_non_draft(self):
        draft = self.make_draft()
        another = Product.objects.create(name="Other", type=Product.Type.SOFTWARE, sales_price_paise=1, cost_price_paise=0)
        other_plan = Plan.objects.create(name="Other plan", primary_product=another, price_paise=1, period=Plan.Period.MONTHLY, available_from=date(2020, 1, 1))
        draft.plan = other_plan
        draft.save()
        with self.assertRaises(ValidationError):
            copy_template_to_subscription(self.template, draft)
        draft.plan = self.plan
        draft.status = Subscription.Status.CONFIRMED
        draft.save()
        with self.assertRaises(ValidationError):
            copy_template_to_subscription(self.template, draft)

    def test_staff_uses_template_in_new_draft_and_quote_copies_validity(self):
        self.client.force_login(self.staff)
        payload = {
            "customer": self.customer.pk, "plan": self.plan.pk, "quote_template": self.template.pk,
            "start_date": self.today.isoformat(), "expiry_date": (self.today + timedelta(days=60)).isoformat(),
            "payment_terms_days": "15",
        }
        response = self.client.post(reverse("subscriptions:new"), payload)
        self.assertEqual(response.status_code, 302)
        draft = Subscription.objects.get()
        self.assertEqual(draft.source_template_id, self.template.pk)
        self.assertEqual(draft.lines.count(), 2)
        self.client.post(reverse("subscriptions:action", args=[draft.pk, "quote"]))
        draft.refresh_from_db()
        self.assertEqual(draft.quote_expires_on, self.today + timedelta(days=14))

    def test_staff_can_select_but_cannot_manage_templates(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("offers:template_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("offers:template_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("offers:template_edit", args=[self.template.pk])).status_code, 403)

    def test_admin_creates_template_with_plan_matched_primary_line(self):
        self.client.force_login(self.admin)
        payload = {
            "name": "Custom", "plan": self.plan.pk, "validity_days": "21", "notes": "",
            "is_active": "on", "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
            "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
            "lines-0-product": self.product.pk, "lines-0-variant": "", "lines-0-is_primary": "on",
            "lines-0-quantity": "2", "lines-0-unit_price": "425.00", "lines-0-taxes": [], "lines-0-position": "0",
        }
        response = self.client.post(reverse("offers:template_create"), payload)
        self.assertEqual(response.status_code, 302)
        created = QuoteTemplate.objects.get(name="Custom")
        self.assertEqual(created.validity_days, 21)
        self.assertEqual(created.lines.get(is_primary=True).unit_price_paise, 42_500)

    def test_template_crud_is_not_available_to_customers(self):
        self.client.force_login(self.customer_user)
        self.assertEqual(self.client.get(reverse("offers:template_list")).status_code, 403)
