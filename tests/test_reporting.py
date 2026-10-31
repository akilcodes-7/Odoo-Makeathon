from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import Customer, Invoice, Payment, Plan, Product, Subscription, SubscriptionLine
from insights.selectors import dashboard_summary


class DashboardReportingTests(TestCase):
    def setUp(self):
        self.today = date.today()
        self.admin = User.objects.create_user("report-admin@example.com", "pw", role=User.Role.ADMIN)
        self.customer_user = User.objects.create_user("report-customer@example.com", "pw", role=User.Role.CUSTOMER)
        self.other_user = User.objects.create_user("report-other@example.com", "pw", role=User.Role.CUSTOMER)
        self.customer = Customer.objects.create(user=self.customer_user, display_name="Report Customer", billing_email=self.customer_user.email)
        self.other = Customer.objects.create(user=self.other_user, display_name="Other Customer", billing_email=self.other_user.email)
        self.product = Product.objects.create(name="Reporting product", type=Product.Type.SERVICE, sales_price_paise=100000, cost_price_paise=0)

    def subscription(self, number, period=Plan.Period.MONTHLY, *, customer=None, status=Subscription.Status.ACTIVE,
                     start=None, expiry=None, paused=False, pause_effective=None, price=10000, quantity=1):
        customer = customer or self.customer
        plan = Plan.objects.create(
            name=f"Plan {number}", primary_product=self.product, price_paise=price,
            period=period, available_from=self.today - timedelta(days=365),
        )
        subscription = Subscription.objects.create(
            number=number, customer=customer, plan=plan, status=status,
            start_date=start or self.today - timedelta(days=30),
            expiry_date=expiry or self.today + timedelta(days=30),
            billing_anchor_date=start or self.today - timedelta(days=30),
            billing_period=period, is_paused=paused, pause_effective_on=pause_effective,
        )
        SubscriptionLine.objects.create(
            subscription=subscription, product=self.product, is_primary=True,
            quantity=quantity, unit_price_paise=price,
        )
        return subscription

    def invoice(self, number, subscription, total, *, due=None, issued=None, period_start=None, status=Invoice.Status.CONFIRMED):
        due = due or self.today
        return Invoice.objects.create(
            number=number, subscription=subscription,
            period_start=period_start or self.today - timedelta(days=30), period_end=self.today,
            invoice_date=issued or min(self.today, due), due_date=due,
            status=status, customer_name=subscription.customer.display_name,
            customer_email=subscription.customer.billing_email,
            subtotal_paise=total, tax_paise=0, total_paise=total,
        )

    def test_dashboard_and_api_report_hand_calculated_metrics(self):
        month = self.subscription("SUB-MONTH", price=10000, quantity=2)
        self.subscription("SUB-DAY", period=Plan.Period.DAILY, price=1200)
        self.subscription("SUB-WEEK", period=Plan.Period.WEEKLY, price=1200)
        self.subscription("SUB-YEAR", period=Plan.Period.YEARLY, price=120000)
        self.subscription("SUB-PAUSED", paused=True, pause_effective=self.today)
        self.subscription("SUB-FUTURE-PAUSE", paused=True, pause_effective=self.today + timedelta(days=2), price=100)
        self.subscription("SUB-EXPIRED", expiry=self.today - timedelta(days=1), price=900000)
        self.subscription("SUB-QUOTE", status=Subscription.Status.CONFIRMED, price=900000)
        overdue = self.invoice("INV-OVERDUE", month, 10000, due=self.today - timedelta(days=1))
        self.invoice("INV-DUE-TODAY", month, 5000, due=self.today, period_start=self.today - timedelta(days=20))
        Payment.objects.create(invoice=overdue, method=Payment.Method.BANK, amount_paise=4000,
                               paid_on=self.today, created_by=self.admin)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("insights:dashboard"))
        self.assertEqual(response.status_code, 200)
        summary = response.context["summary"]
        self.assertEqual(summary["active_subscriptions"], 5)
        self.assertEqual(summary["mrr_before_discounts_paise"], 71800)
        self.assertEqual(summary["outstanding_paise"], 11000)
        self.assertEqual(summary["outstanding_invoice_count"], 2)
        self.assertEqual(summary["overdue_paise"], 6000)
        self.assertEqual(summary["overdue_invoice_count"], 1)
        self.assertEqual(summary["collected_paise"], 4000)
        self.assertEqual(summary["invoiced_paise"], 15000)

        api = self.client.get(reverse("insights:summary_api"))
        self.assertEqual(api.status_code, 200)
        payload = api.json()
        self.assertEqual(payload["currency"], "INR")
        self.assertEqual(payload["mrr_before_discounts_paise"], 71800)
        self.assertEqual(payload["range_start"], self.today.replace(day=1).isoformat())
        self.assertEqual(payload["collection_days"][0]["amount_paise"], 4000)

    def test_customer_dashboard_and_json_are_own_account_only(self):
        own_sub = self.subscription("SUB-OWN")
        other_sub = self.subscription("SUB-OTHER", customer=self.other, price=999999)
        own_invoice = self.invoice("INV-OWN", own_sub, 2000)
        self.invoice("INV-OWN-DRAFT", own_sub, 4000, status=Invoice.Status.DRAFT,
                     period_start=self.today - timedelta(days=20))
        other_invoice = self.invoice("INV-OTHER", other_sub, 900000)
        Payment.objects.create(invoice=own_invoice, method=Payment.Method.CASH, amount_paise=500,
                               paid_on=self.today, created_by=self.admin)
        Payment.objects.create(invoice=other_invoice, method=Payment.Method.CASH, amount_paise=900000,
                               paid_on=self.today, created_by=self.admin)
        self.client.force_login(self.customer_user)
        response = self.client.get(reverse("insights:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([s.number for s in response.context["subscriptions_page"]], ["SUB-OWN"])
        self.assertEqual([i.number for i in response.context["invoices_page"]], ["INV-OWN"])
        self.assertEqual(response.context["summary"]["outstanding_paise"], 1500)
        payload = self.client.get(reverse("insights:summary_api")).json()
        self.assertEqual(payload["collected_paise"], 500)
        self.assertEqual(payload["mrr_before_discounts_paise"], 10000)
        self.assertNotIn("other_invoice", payload)

    def test_invalid_date_range_and_status_are_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("insights:summary_api"), {
            "start": self.today.isoformat(), "end": (self.today - timedelta(days=1)).isoformat(),
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("on or before", response.json()["error"])
        response = self.client.get(reverse("insights:dashboard"), {"subscription_status": "MADE_UP"})
        self.assertEqual(response.status_code, 400)

    def test_empty_set_returns_zero_metrics(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("insights:summary_api"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["active_subscriptions"], 0)
        self.assertEqual(payload["mrr_before_discounts_paise"], 0)
        self.assertEqual(payload["outstanding_paise"], 0)
        self.assertEqual(payload["collected_paise"], 0)
