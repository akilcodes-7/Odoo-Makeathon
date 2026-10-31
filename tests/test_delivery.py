from datetime import date, timedelta
from unittest.mock import patch

from django.core import mail
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from core.models import Customer, Invoice, Plan, Product, Subscription
from core.services.exceptions import DomainValidationError
from finance.delivery_views import invoice_print
from finance.services.delivery import send_invoice


class InvoiceDeliveryTests(TestCase):
    def setUp(self):
        today = timezone.localdate()
        self.staff = User.objects.create_user("delivery-staff@example.com", "pw", role=User.Role.STAFF)
        self.customer_user = User.objects.create_user("delivery-customer@example.com", "pw", role=User.Role.CUSTOMER)
        self.other_user = User.objects.create_user("other-customer@example.com", "pw", role=User.Role.CUSTOMER)
        self.customer = Customer.objects.create(user=self.customer_user, display_name="Snapshot Name", billing_email="snapshot@example.com", billing_address="12 Saved Road")
        self.other_customer = Customer.objects.create(user=self.other_user, display_name="Other", billing_email="other@example.com")
        product = Product.objects.create(name="Service", type=Product.Type.SERVICE, sales_price_paise=10000, cost_price_paise=2500)
        plan = Plan.objects.create(name="Monthly", primary_product=product, price_paise=10000, period=Plan.Period.MONTHLY, available_from=today)
        subscription = Subscription.objects.create(
            number="SUB-DELIVERY-1", customer=self.customer, plan=plan, status=Subscription.Status.ACTIVE,
            start_date=today, expiry_date=today + timedelta(days=31), billing_anchor_date=today,
            billing_period=Plan.Period.MONTHLY,
        )
        self.invoice = Invoice.objects.create(
            number="INV-DELIVERY-1", subscription=subscription, period_start=today,
            period_end=today + timedelta(days=31), invoice_date=today, due_date=today,
            status=Invoice.Status.CONFIRMED, customer_name="Snapshot Name", customer_email="snapshot@example.com",
            customer_address="12 Saved Road", subtotal_paise=10000, tax_paise=1800, total_paise=11800,
        )
        other_subscription = Subscription.objects.create(
            number="SUB-DELIVERY-2", customer=self.other_customer, plan=plan, status=Subscription.Status.ACTIVE,
            start_date=today, expiry_date=today + timedelta(days=31), billing_anchor_date=today,
            billing_period=Plan.Period.MONTHLY,
        )
        self.other_invoice = Invoice.objects.create(
            number="INV-DELIVERY-2", subscription=other_subscription, period_start=today,
            period_end=today + timedelta(days=31), invoice_date=today, due_date=today,
            status=Invoice.Status.CONFIRMED, customer_name="Other", customer_email="other@example.com",
            subtotal_paise=10000, tax_paise=0, total_paise=10000,
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_send_uses_snapshot_address_and_records_handoff_without_changing_financial_state(self):
        sent = send_invoice(self.invoice.pk, invoice_url="https://example.test/invoices/1/print/", actor=self.staff)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["snapshot@example.com"])
        self.assertIn("/invoices/1/print/", mail.outbox[0].body)
        self.assertIsNotNone(sent.sent_at)
        self.invoice.refresh_from_db()
        self.assertEqual((self.invoice.status, self.invoice.total_paise), (Invoice.Status.CONFIRMED, 11800))

    def test_invalid_snapshot_email_and_non_sendable_status_are_rejected(self):
        self.invoice.customer_email = "not an email"
        self.invoice.save(update_fields=["customer_email"])
        with self.assertRaises(DomainValidationError):
            send_invoice(self.invoice.pk, invoice_url="https://example.test/", actor=self.staff)
        self.invoice.customer_email = "snapshot@example.com"
        self.invoice.status = Invoice.Status.DRAFT
        self.invoice.save(update_fields=["customer_email", "status"])
        with self.assertRaises(DomainValidationError):
            send_invoice(self.invoice.pk, invoice_url="https://example.test/", actor=self.staff)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_backend_failure_does_not_mark_invoice_sent(self):
        with patch("finance.services.delivery.EmailMultiAlternatives.send", side_effect=OSError("smtp unavailable")):
            with self.assertRaises(OSError):
                send_invoice(self.invoice.pk, invoice_url="https://example.test/", actor=self.staff)
        self.invoice.refresh_from_db()
        self.assertIsNone(self.invoice.sent_at)
        self.assertEqual(self.invoice.status, Invoice.Status.CONFIRMED)

    def test_customer_print_uses_saved_snapshot_and_foreign_invoice_is_404(self):
        factory = RequestFactory()
        request = factory.get(f"/invoices/{self.invoice.pk}/print/")
        request.user = self.customer_user
        response = invoice_print(request, self.invoice.pk)
        self.assertContains(response, "Snapshot Name")
        self.assertContains(response, "12 Saved Road")
        self.assertNotContains(response, "2500")
        foreign_request = factory.get(f"/invoices/{self.other_invoice.pk}/print/")
        foreign_request.user = self.customer_user
        with self.assertRaises(Http404):
            invoice_print(foreign_request, self.other_invoice.pk)
