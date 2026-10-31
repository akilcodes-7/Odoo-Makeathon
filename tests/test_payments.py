from datetime import date, timedelta
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.models import Customer, Invoice, Plan, Product, Subscription
from core.services.exceptions import DomainValidationError
from finance.services.payments import get_invoice_balance, invoice_is_overdue, record_payment


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin-pay@example.com", "pw", role=User.Role.ADMIN)
        self.staff = User.objects.create_user("staff-pay@example.com", "pw", role=User.Role.STAFF)
        self.customer_user = User.objects.create_user("customer-pay@example.com", "pw", role=User.Role.CUSTOMER)
        customer = Customer.objects.create(user=self.customer_user, display_name="Payment Customer", billing_email=self.customer_user.email)
        product = Product.objects.create(name="Hosting", type=Product.Type.SERVICE, sales_price_paise=10000, cost_price_paise=0)
        plan = Plan.objects.create(name="Monthly", primary_product=product, price_paise=10000, period=Plan.Period.MONTHLY, available_from=date.today())
        subscription = Subscription.objects.create(
            number="SUB-PAY-1", customer=customer, plan=plan, status=Subscription.Status.ACTIVE,
            start_date=date.today(), expiry_date=date.today() + timedelta(days=30),
            billing_anchor_date=date.today(), billing_period=Plan.Period.MONTHLY,
        )
        self.invoice = Invoice.objects.create(
            number="INV-PAY-1", subscription=subscription, period_start=date.today(),
            period_end=date.today() + timedelta(days=30), invoice_date=date.today(), due_date=date.today(),
            status=Invoice.Status.CONFIRMED, customer_name=customer.display_name,
            customer_email=customer.billing_email, subtotal_paise=10000, tax_paise=0, total_paise=10000,
        )

    def record(self, **changes):
        payload = {
            "amount_paise": 4000, "method": "BANK", "paid_on": date.today(),
            "note": "", "idempotency_key": uuid4(), "actor": self.staff,
        }
        payload.update(changes)
        return record_payment(self.invoice.pk, **payload)

    def test_partial_and_full_payment_reconcile_and_transition_paid(self):
        self.record()
        self.assertEqual(get_invoice_balance(self.invoice.pk), 6000)
        self.assertEqual(Invoice.objects.get(pk=self.invoice.pk).status, Invoice.Status.CONFIRMED)
        self.record(amount_paise=6000)
        self.assertEqual(get_invoice_balance(self.invoice.pk), 0)
        self.assertEqual(Invoice.objects.get(pk=self.invoice.pk).status, Invoice.Status.PAID)

    def test_same_key_replay_returns_original_and_conflict_is_rejected(self):
        key = uuid4()
        first = self.record(idempotency_key=key)
        replay = self.record(idempotency_key=key)
        self.assertEqual(first.pk, replay.pk)
        self.assertEqual(self.invoice.payments.count(), 1)
        with self.assertRaises(DomainValidationError) as caught:
            self.record(idempotency_key=key, amount_paise=5000)
        self.assertEqual(caught.exception.code, "idempotency_conflict")

    def test_overdue_requires_confirmed_past_due_invoice_with_balance(self):
        today = date.today()
        self.invoice.due_date = today
        self.invoice.save(update_fields=["due_date"])
        self.assertFalse(invoice_is_overdue(self.invoice.pk, as_of=today))
        self.assertTrue(invoice_is_overdue(self.invoice.pk, as_of=today + timedelta(days=1)))
        self.record(amount_paise=10000)
        self.assertFalse(invoice_is_overdue(self.invoice.pk, as_of=today + timedelta(days=1)))

    def test_invalid_amount_date_method_and_invoice_states_rejected(self):
        for amount in (0, -1, 10001):
            with self.subTest(amount=amount), self.assertRaises(DomainValidationError):
                self.record(amount_paise=amount)
        with self.assertRaises(DomainValidationError):
            self.record(method="BOGUS")
        with self.assertRaises(DomainValidationError):
            self.record(paid_on=date.today() + timedelta(days=1))
        self.invoice.status = Invoice.Status.DRAFT
        self.invoice.save(update_fields=["status"])
        with self.assertRaises(DomainValidationError):
            self.record()


class PaymentViewTests(PaymentServiceTests):
    def test_staff_can_record_and_list_but_customer_is_denied(self):
        from django.test import Client

        client = Client()
        client.force_login(self.staff)
        list_url = reverse("finance_payments:list")
        new_url = reverse("finance_payments:new", args=[self.invoice.pk])
        self.assertEqual(client.get(list_url).status_code, 200)
        response = client.get(new_url)
        self.assertEqual(response.status_code, 200)
        key = response.context["form"].initial["idempotency_key"]
        self.assertEqual(client.post(new_url, {
            "amount": "100.00", "method": "CASH", "paid_on": date.today().isoformat(),
            "note": "Paid at desk", "idempotency_key": key,
        }).status_code, 302)
        self.assertEqual(Invoice.objects.get(pk=self.invoice.pk).status, Invoice.Status.PAID)
        client.force_login(self.customer_user)
        self.assertEqual(client.get(list_url).status_code, 403)
        self.assertEqual(client.get(new_url).status_code, 403)
