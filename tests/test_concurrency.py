from concurrent.futures import ThreadPoolExecutor
from datetime import date
import os
from threading import Barrier
from unittest import skipUnless
from uuid import uuid4

from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone

from accounts.models import User
from core.models import (
    Customer, Discount, Invoice, Plan, Product, Subscription, SubscriptionLine,
)
from core.services.billing import create_invoice_for_period
from core.services.exceptions import DomainValidationError
from finance.services.payments import record_payment


@skipUnless(os.environ.get("TEST_DATABASE_PATH"), "run with TEST_DATABASE_PATH set to an on-disk SQLite database")
class ConcurrentFinancialWriteTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.admin = User.objects.create_user("race-admin@example.test", "ValidPassword!", role=User.Role.ADMIN)
        self.product = Product.objects.create(name="Race Product", type=Product.Type.SOFTWARE, sales_price_paise=10_000, cost_price_paise=1_000)
        self.plan = Plan.objects.create(name="Race Monthly", primary_product=self.product, price_paise=10_000, period=Plan.Period.MONTHLY, available_from=date(2020, 1, 1))
        self.customer = Customer.objects.create(display_name="Race Customer", billing_email="race@example.test")

    def make_subscription(self, suffix):
        subscription = Subscription.objects.create(
            number=f"RACE-{suffix}", customer=self.customer, plan=self.plan,
            status=Subscription.Status.ACTIVE, start_date=date(2024, 1, 1), expiry_date=date(2024, 12, 31),
            billing_anchor_date=date(2024, 1, 1), next_invoice_date=date(2024, 1, 1),
            billing_period=Plan.Period.MONTHLY,
        )
        SubscriptionLine.objects.create(
            subscription=subscription, product=self.product, is_primary=True,
            quantity=1, unit_price_paise=10_000,
        )
        return subscription

    def concurrently(self, operations):
        barrier = Barrier(len(operations))

        def run(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(run, operations))

    def test_concurrent_same_period_billing_creates_one_invoice_and_advances_once(self):
        subscription = self.make_subscription("BILL")
        results = self.concurrently([
            lambda: create_invoice_for_period(subscription.pk, date(2024, 1, 1), as_of=date(2024, 1, 1), actor=self.admin),
            lambda: create_invoice_for_period(subscription.pk, date(2024, 1, 1), as_of=date(2024, 1, 1), actor=self.admin),
        ])
        self.assertEqual(results[0].pk, results[1].pk)
        self.assertEqual(Invoice.objects.filter(subscription=subscription).count(), 1)
        subscription.refresh_from_db()
        self.assertEqual(subscription.billing_period_index, 1)

    def test_competing_invoices_reserve_only_one_use_of_discount(self):
        first = self.make_subscription("DISC-A")
        second = self.make_subscription("DISC-B")
        Discount.objects.create(
            name="One use", kind=Discount.Kind.FIXED, amount_paise=1_000,
            scope=Discount.Scope.SUBSCRIPTION, starts_on=date(2020, 1, 1),
            max_uses=1, used_count=0, is_active=True,
        )
        self.concurrently([
            lambda: create_invoice_for_period(first.pk, date(2024, 1, 1), as_of=date(2024, 1, 1), actor=self.admin),
            lambda: create_invoice_for_period(second.pk, date(2024, 1, 1), as_of=date(2024, 1, 1), actor=self.admin),
        ])
        rule = Discount.objects.get(name="One use")
        self.assertEqual(rule.used_count, 1)
        self.assertEqual(Invoice.objects.filter(discount_redemption__discount=rule).count(), 1)

    def test_distinct_concurrent_payments_cannot_overpay(self):
        subscription = self.make_subscription("PAY")
        invoice = Invoice.objects.create(
            number="RACE-INV", subscription=subscription, period_start=date(2024, 1, 1), period_end=date(2024, 2, 1),
            invoice_date=timezone.localdate(), due_date=timezone.localdate(), status=Invoice.Status.CONFIRMED,
            customer_name="Race Customer", customer_email="race@example.test", subtotal_paise=10_000,
            discount_paise=0, tax_paise=0, total_paise=10_000,
        )

        def payment(key):
            try:
                return record_payment(
                    invoice.pk, amount_paise=7_000, method="BANK", paid_on=timezone.localdate(),
                    note="Concurrent", idempotency_key=key, actor=self.admin,
                )
            except DomainValidationError as exc:
                return exc

        outcomes = self.concurrently([lambda: payment(uuid4()), lambda: payment(uuid4())])
        self.assertEqual(sum(not isinstance(result, DomainValidationError) for result in outcomes), 1)
        invoice.refresh_from_db()
        self.assertLessEqual(sum(invoice.payments.values_list("amount_paise", flat=True)), invoice.total_paise)
        self.assertEqual(invoice.payments.count(), 1)
