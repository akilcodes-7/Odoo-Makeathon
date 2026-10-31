from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import Customer, Invoice, Plan, Product, Subscription


class CustomerPortalTests(TestCase):
    def setUp(self):
        today = timezone.localdate()
        self.today = today
        self.user = User.objects.create_user("portal@example.com", "test-password", role=User.Role.CUSTOMER)
        self.other_user = User.objects.create_user("foreign@example.com", "test-password", role=User.Role.CUSTOMER)
        self.staff = User.objects.create_user("portal-staff@example.com", "test-password", role=User.Role.STAFF)
        self.customer = Customer.objects.create(
            user=self.user, display_name="Portal Customer", billing_email="portal@example.com"
        )
        self.other_customer = Customer.objects.create(
            user=self.other_user, display_name="Other Customer", billing_email="foreign@example.com"
        )
        product = Product.objects.create(
            name="Private Service", type=Product.Type.SERVICE,
            sales_price_paise=12000, cost_price_paise=4700,
        )
        plan = Plan.objects.create(
            name="Monthly plan", primary_product=product, price_paise=12000,
            period=Plan.Period.MONTHLY, available_from=today,
        )
        self.subscription = self.make_subscription("SUB-PORTAL-1", self.customer, plan)
        self.other_subscription = self.make_subscription("SUB-PORTAL-2", self.other_customer, plan)
        self.invoice = self.make_invoice("INV-PORTAL-1", self.subscription, Invoice.Status.CONFIRMED)
        self.paid_invoice = self.make_invoice("INV-PORTAL-PAID", self.subscription, Invoice.Status.PAID)
        self.foreign_invoice = self.make_invoice("INV-PORTAL-2", self.other_subscription, Invoice.Status.CONFIRMED)
        self.draft_invoice = self.make_invoice("INV-PORTAL-DRAFT", self.subscription, Invoice.Status.DRAFT)
        self.cancelled_invoice = self.make_invoice("INV-PORTAL-CANCEL", self.subscription, Invoice.Status.CANCELLED)

    def make_subscription(self, number, customer, plan, **kwargs):
        return Subscription.objects.create(
            number=number, customer=customer, plan=plan, status=Subscription.Status.ACTIVE,
            start_date=self.today - timedelta(days=5), expiry_date=self.today + timedelta(days=30),
            billing_anchor_date=self.today - timedelta(days=5), billing_period=Plan.Period.MONTHLY,
            **kwargs,
        )

    def make_invoice(self, number, subscription, status):
        offset = Invoice.objects.filter(subscription=subscription).count() * 31
        period_start = self.today - timedelta(days=5 + offset)
        return Invoice.objects.create(
            number=number, subscription=subscription,
            period_start=period_start, period_end=period_start + timedelta(days=30),
            invoice_date=self.today, due_date=self.today + timedelta(days=7), status=status,
            customer_name=subscription.customer.display_name,
            customer_email=subscription.customer.billing_email,
            subtotal_paise=12000, tax_paise=0, total_paise=12000,
        )

    def login_customer(self):
        self.client.force_login(self.user)

    def test_own_summary_and_lists_show_only_customers_data(self):
        self.login_customer()
        dashboard = self.client.get(reverse("portal:dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "SUB-PORTAL-1")
        self.assertNotContains(dashboard, "SUB-PORTAL-2")
        self.assertNotContains(dashboard, "4700")
        subs = self.client.get(reverse("portal:subscriptions"))
        self.assertContains(subs, "SUB-PORTAL-1")
        self.assertNotContains(subs, "SUB-PORTAL-2")
        invoices = self.client.get(reverse("portal:invoices"))
        self.assertContains(invoices, self.invoice.number)
        self.assertContains(invoices, self.paid_invoice.number)
        self.assertNotContains(invoices, self.foreign_invoice.number)
        self.assertNotContains(invoices, self.draft_invoice.number)
        self.assertNotContains(invoices, self.cancelled_invoice.number)

    def test_foreign_subscription_and_invoice_ids_return_404(self):
        self.login_customer()
        self.assertEqual(self.client.get(reverse("portal:subscription_detail", args=[self.other_subscription.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("portal:invoice_detail", args=[self.foreign_invoice.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("portal:invoice_detail", args=[self.draft_invoice.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("finance_delivery:print", args=[self.foreign_invoice.pk])).status_code, 404)

    def test_action_requires_post_and_ignores_posted_customer_id(self):
        self.login_customer()
        url = reverse("portal:subscription_action", args=[self.subscription.pk, "pause"])
        self.assertEqual(self.client.get(url).status_code, 403)
        with patch("portal.views.pause_subscription") as pause:
            response = self.client.post(url, {"customer_id": self.other_customer.pk})
        self.assertRedirects(response, reverse("portal:subscription_detail", args=[self.subscription.pk]))
        pause.assert_called_once_with(self.subscription.pk, actor=self.user, reason="")

    def test_allowed_actions_call_shared_lifecycle_helpers(self):
        self.login_customer()
        actions = [
            ("close", "transition_subscription", (self.subscription.pk, "CLOSED")),
            ("pause", "pause_subscription", (self.subscription.pk,)),
            ("resume", "resume_subscription", (self.subscription.pk,)),
            ("renew", "renew_subscription", (self.subscription.pk,)),
        ]
        for action, helper, expected_prefix in actions:
            with self.subTest(action=action), patch(f"portal.views.{helper}") as mocked:
                mocked.return_value = self.subscription
                response = self.client.post(reverse("portal:subscription_action", args=[self.subscription.pk, action]))
                self.assertEqual(response.status_code, 302)
                called = mocked.call_args
                self.assertEqual(called.args[:len(expected_prefix)], expected_prefix)
                self.assertEqual(called.kwargs["actor"], self.user)

    def test_contract_flags_and_lifecycle_state_block_forbidden_requests(self):
        self.login_customer()
        # This contract's stored flag is false, so the service rejects a
        # customer POST even if they construct it without using the UI button.
        pause_url = reverse("portal:subscription_action", args=[self.subscription.pk, "pause"])
        response = self.client.post(pause_url)
        self.assertEqual(response.status_code, 302)
        self.subscription.refresh_from_db()
        self.assertFalse(self.subscription.is_paused)
        self.subscription.closable_snapshot = False
        self.subscription.save(update_fields=["closable_snapshot"])
        close_url = reverse("portal:subscription_action", args=[self.subscription.pk, "close"])
        self.client.post(close_url)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, Subscription.Status.ACTIVE)

    def test_renewal_creates_draft_and_reports_request_not_active_renewal(self):
        self.login_customer()
        self.subscription.status = Subscription.Status.CLOSED
        self.subscription.closed_on = self.today - timedelta(days=1)
        self.subscription.save(update_fields=["status", "closed_on"])
        response = self.client.post(reverse("portal:subscription_action", args=[self.subscription.pk, "renew"]))
        self.assertRedirects(response, reverse("portal:subscription_detail", args=[self.subscription.pk]))
        successor = Subscription.objects.get(renewed_from=self.subscription)
        self.assertEqual(successor.status, Subscription.Status.DRAFT)
        detail = self.client.get(reverse("portal:subscription_detail", args=[self.subscription.pk]))
        self.assertContains(detail, "Renewal requested")
        self.assertContains(detail, "awaiting staff review")

    def test_foreign_action_id_is_not_passed_to_lifecycle_service(self):
        self.login_customer()
        with patch("portal.views.pause_subscription") as pause:
            response = self.client.post(reverse("portal:subscription_action", args=[self.other_subscription.pk, "pause"]))
        self.assertEqual(response.status_code, 404)
        pause.assert_not_called()

    def test_invoice_detail_links_to_scoped_print_and_profile_entry_points_to_own_profile(self):
        self.login_customer()
        response = self.client.get(reverse("portal:invoice_detail", args=[self.invoice.pk]))
        self.assertContains(response, reverse("finance_delivery:print", args=[self.invoice.pk]))
        self.assertEqual(self.client.get(reverse("portal:profile")).status_code, 302)
        self.assertRedirects(self.client.get(reverse("portal:profile")), reverse("customers:profile"))

    def test_non_customer_cannot_open_portal(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("portal:dashboard")).status_code, 403)
