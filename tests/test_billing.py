from datetime import date
from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from core.models import Customer, Invoice, Plan, Product, Subscription, SubscriptionLine, Tax
from core.services.billing import create_invoice_for_period, run_due_billing


class BillingServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin@example.com", password="ValidPassword!", role=User.Role.ADMIN)
        self.customer = Customer.objects.create(display_name="Acme", billing_email="billing@example.com", billing_address="1 Old Road")
        self.product = Product.objects.create(name="Cloud", type=Product.Type.SOFTWARE, sales_price_paise=100_000, cost_price_paise=10_000)
        self.tax = Tax.objects.create(name="GST", rate_bps=1_800)
        self.plan = Plan.objects.create(
            name="Monthly", primary_product=self.product, price_paise=100_000,
            period=Plan.Period.MONTHLY, min_quantity=1, available_from=date(2020, 1, 1),
        )

    def make_active(self, *, start=date(2024, 1, 31), expiry=date(2024, 5, 30), quantity=2):
        subscription = Subscription.objects.create(
            number="SUB-TEMP", customer=self.customer, plan=self.plan,
            status=Subscription.Status.ACTIVE, start_date=start, expiry_date=expiry,
            payment_terms_days=15, billing_anchor_date=start, billing_period_index=0,
            next_invoice_date=start, billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=False, closable_snapshot=True,
            pausable_snapshot=False, renewable_snapshot=True, min_quantity_snapshot=1,
        )
        subscription.number = f"SUB-{subscription.pk:06d}"
        subscription.save(update_fields=["number"])
        line = SubscriptionLine.objects.create(
            subscription=subscription, product=self.product, is_primary=True,
            quantity=quantity, unit_price_paise=self.plan.price_paise,
        )
        line.taxes.add(self.tax)
        return subscription

    def test_invoice_reconciles_tax_and_snapshots_billing_identity(self):
        subscription = self.make_active()
        invoice = create_invoice_for_period(subscription.pk, date(2024, 1, 31), as_of=date(2024, 1, 31), actor=self.admin)
        self.assertEqual(invoice.subtotal_paise, 200_000)
        self.assertEqual(invoice.discount_paise, 0)
        self.assertEqual(invoice.tax_paise, 36_000)
        self.assertEqual(invoice.total_paise, 236_000)
        self.assertEqual(invoice.due_date, date(2024, 2, 15))
        self.assertEqual(invoice.customer_address, "1 Old Road")
        line = invoice.lines.get()
        self.assertEqual(line.product_name, "Cloud")
        self.assertEqual(line.tax_snapshots.get().amount_paise, 36_000)
        self.customer.billing_address = "2 New Road"
        self.customer.save()
        self.product.name = "Changed"
        self.product.save()
        self.tax.rate_bps = 500
        self.tax.save()
        invoice.refresh_from_db()
        self.assertEqual(invoice.customer_address, "1 Old Road")
        self.assertEqual(invoice.lines.get().product_name, "Cloud")
        self.assertEqual(invoice.lines.get().tax_snapshots.get().rate_bps, 1_800)

    def test_same_period_never_creates_a_duplicate_or_double_advances(self):
        subscription = self.make_active()
        first = create_invoice_for_period(subscription.pk, date(2024, 1, 31), as_of=date(2024, 1, 31))
        repeated = create_invoice_for_period(subscription.pk, date(2024, 1, 31), as_of=date(2024, 1, 31))
        self.assertEqual(first.pk, repeated.pk)
        self.assertEqual(Invoice.objects.filter(subscription=subscription).count(), 1)
        subscription.refresh_from_db()
        self.assertEqual(subscription.next_invoice_date, date(2024, 2, 29))
        self.assertEqual(subscription.billing_period_index, 1)

    def test_terminal_period_is_prorated_using_actual_service_days(self):
        subscription = self.make_active(expiry=date(2024, 3, 5), quantity=1)
        create_invoice_for_period(subscription.pk, date(2024, 1, 31), as_of=date(2024, 1, 31))
        invoice = create_invoice_for_period(subscription.pk, date(2024, 2, 29), as_of=date(2024, 2, 29))
        line = invoice.lines.get()
        self.assertEqual((line.period_numerator_days, line.period_denominator_days), (6, 31))
        self.assertEqual(line.subtotal_paise, 19_355)
        self.assertEqual(invoice.period_end, date(2024, 3, 6))

    def test_catch_up_is_bounded_and_preserves_earliest_due_cursor(self):
        subscription = self.make_active(expiry=date(2024, 5, 30))
        first = run_due_billing(as_of=date(2024, 4, 30), subscription_ids=[subscription.pk], max_periods_per_subscription=1)
        self.assertEqual(len(first.created_ids), 1)
        self.assertEqual(first.remaining_due_count, 1)
        subscription.refresh_from_db()
        self.assertEqual(subscription.next_invoice_date, date(2024, 2, 29))
        second = run_due_billing(as_of=date(2024, 4, 30), subscription_ids=[subscription.pk], max_periods_per_subscription=1)
        self.assertEqual(len(second.created_ids), 1)
        self.assertEqual(second.remaining_due_count, 1)
        subscription.refresh_from_db()
        self.assertEqual(subscription.next_invoice_date, date(2024, 3, 31))
        third = run_due_billing(as_of=date(2024, 4, 30), subscription_ids=[subscription.pk], max_periods_per_subscription=1)
        self.assertEqual(len(third.created_ids), 1)
        self.assertEqual(third.remaining_due_count, 1)
        subscription.refresh_from_db()
        self.assertEqual(subscription.next_invoice_date, date(2024, 4, 30))
        fourth = run_due_billing(as_of=date(2024, 4, 30), subscription_ids=[subscription.pk], max_periods_per_subscription=1)
        self.assertEqual(len(fourth.created_ids), 1)
        self.assertEqual(fourth.remaining_due_count, 0)

    @patch("offers.services.discounts.reserve_discount_usage", side_effect=RuntimeError("reservation failed"))
    @patch("offers.services.discounts.get_applicable_discounts")
    def test_failed_discount_reservation_rolls_back_invoice_and_cursor(self, get_discounts, reserve):
        from core.services.pricing import DiscountApplication

        subscription = self.make_active(quantity=1)
        get_discounts.return_value = [DiscountApplication(
            discount_id=1, name="Rule", kind="FIXED", value_paise=1,
            value_bps=None, line_discounts=((subscription.lines.get().pk, 1),), total_discount_paise=1,
        )]
        result = run_due_billing(as_of=date(2024, 1, 31), subscription_ids=[subscription.pk])
        self.assertTrue(result.errors)
        self.assertEqual(Invoice.objects.filter(subscription=subscription).count(), 0)
        subscription.refresh_from_db()
        self.assertEqual(subscription.billing_period_index, 0)
        self.assertEqual(subscription.next_invoice_date, date(2024, 1, 31))
