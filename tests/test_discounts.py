from datetime import date
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase

from accounts.models import User
from core.models import (
    Customer, Discount, DiscountRedemption, Invoice, Plan, Product,
    Subscription, SubscriptionLine,
)
from core.services.billing import create_invoice_for_period
from core.services.exceptions import DiscountCapacityChanged
from core.services.pricing import BillingPeriod, LineBase
from offers.forms import DiscountForm
from offers.services.discounts import get_applicable_discounts, reserve_discount_usage


class DiscountServiceTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(display_name="Acme", billing_email="billing@example.test")
        self.product_a = Product.objects.create(name="Alpha", type=Product.Type.SOFTWARE, sales_price_paise=10_000, cost_price_paise=0)
        self.product_b = Product.objects.create(name="Beta", type=Product.Type.ADDON, sales_price_paise=10_000, cost_price_paise=0)
        self.plan = Plan.objects.create(
            name="Monthly", primary_product=self.product_a, price_paise=10_000,
            period=Plan.Period.MONTHLY, available_from=date(2020, 1, 1),
        )
        self.subscription = Subscription.objects.create(
            number="SUB-X", customer=self.customer, plan=self.plan,
            status=Subscription.Status.ACTIVE, start_date=date(2024, 1, 1), expiry_date=date(2024, 12, 31),
            billing_anchor_date=date(2024, 1, 1), next_invoice_date=date(2024, 1, 1),
            billing_period=Subscription.Period.MONTHLY,
        )
        self.line_a = SubscriptionLine.objects.create(
            subscription=self.subscription, product=self.product_a, is_primary=True,
            quantity=2, unit_price_paise=10_000,
        )
        self.line_b = SubscriptionLine.objects.create(
            subscription=self.subscription, product=self.product_b,
            quantity=1, unit_price_paise=5_000, position=1,
        )
        self.bases = [
            LineBase(self.line_a.pk, self.product_a.pk, 2, 10_000, 20_000, ()),
            LineBase(self.line_b.pk, self.product_b.pk, 1, 5_000, 5_000, ()),
        ]
        self.period = BillingPeriod(date(2024, 2, 1), date(2024, 3, 1), date(2024, 3, 1))

    def make_rule(self, **kwargs):
        values = dict(
            name="Rule", kind=Discount.Kind.FIXED, amount_paise=3_000,
            scope=Discount.Scope.SUBSCRIPTION, min_purchase_paise=0, min_quantity=0,
            starts_on=date(2024, 1, 1), is_active=True,
        )
        values.update(kwargs)
        return Discount.objects.create(**values)

    def test_fixed_amount_is_capped_and_allocated_by_largest_remainder_then_line_id(self):
        rule = self.make_rule(amount_paise=10_001)
        result = get_applicable_discounts(self.subscription, self.period, line_bases=self.bases)[0]
        self.assertEqual(result.discount_id, rule.pk)
        self.assertEqual(result.total_discount_paise, 10_001)
        self.assertEqual(dict(result.line_discounts), {self.line_a.pk: 8_001, self.line_b.pk: 2_000})
        self.assertEqual(sum(dict(result.line_discounts).values()), result.total_discount_paise)

    def test_fixed_amount_caps_to_eligible_subtotal(self):
        self.make_rule(amount_paise=100_000)
        result = get_applicable_discounts(self.subscription, self.period, line_bases=self.bases)[0]
        self.assertEqual(result.total_discount_paise, 25_000)
        self.assertEqual(dict(result.line_discounts), {self.line_a.pk: 20_000, self.line_b.pk: 5_000})

    def test_largest_remainder_tie_goes_to_lowest_source_line_id(self):
        self.make_rule(amount_paise=1)
        equal_bases = [
            LineBase(self.line_b.pk, self.product_b.pk, 1, 1, 1, ()),
            LineBase(self.line_a.pk, self.product_a.pk, 1, 1, 1, ()),
        ]
        result = get_applicable_discounts(self.subscription, self.period, line_bases=equal_bases)[0]
        self.assertEqual(result.line_discounts, ((self.line_a.pk, 1),))

    def test_percentage_rounds_each_line_half_up_and_does_not_exceed_base(self):
        self.make_rule(kind=Discount.Kind.PERCENT, amount_paise=None, percent_bps=3_333)
        result = get_applicable_discounts(self.subscription, self.period, line_bases=self.bases)[0]
        self.assertEqual(dict(result.line_discounts), {self.line_a.pk: 6_666, self.line_b.pk: 1_667})
        self.assertEqual(result.total_discount_paise, 8_333)

    def test_product_scope_and_both_minimums_are_applied_to_eligible_lines(self):
        rule = self.make_rule(scope=Discount.Scope.PRODUCTS, min_purchase_paise=20_000, min_quantity=2)
        rule.products.add(self.product_a)
        result = get_applicable_discounts(self.subscription, self.period, line_bases=self.bases)
        self.assertEqual(len(result), 1)
        self.assertEqual(dict(result[0].line_discounts), {self.line_a.pk: 3_000})
        rule.min_purchase_paise = 20_001
        rule.save()
        self.assertEqual(get_applicable_discounts(self.subscription, self.period, line_bases=self.bases), [])
        rule.min_purchase_paise = 0
        rule.min_quantity = 3
        rule.save()
        self.assertEqual(get_applicable_discounts(self.subscription, self.period, line_bases=self.bases), [])

    def test_start_and_end_dates_are_inclusive_and_exhausted_or_inactive_rules_are_ignored(self):
        starts = self.make_rule(starts_on=self.period.start)
        ends = self.make_rule(name="End", starts_on=date(2024, 1, 1), ends_on=self.period.start)
        expired = self.make_rule(name="Expired", ends_on=date(2024, 1, 31))
        inactive = self.make_rule(name="Inactive", is_active=False)
        exhausted = self.make_rule(name="Full", max_uses=1, used_count=1)
        ids = {item.discount_id for item in get_applicable_discounts(self.subscription, self.period, line_bases=self.bases)}
        self.assertEqual(ids, {starts.pk, ends.pk})
        self.assertNotIn(expired.pk, ids)
        self.assertNotIn(inactive.pk, ids)
        self.assertNotIn(exhausted.pk, ids)

    def test_best_saving_then_lowest_id_is_deterministic_and_no_stacking(self):
        lower = self.make_rule(name="Lower", amount_paise=4_000)
        tied = self.make_rule(name="Tied", amount_paise=4_000)
        greater = self.make_rule(name="Greater", kind=Discount.Kind.PERCENT, amount_paise=None, percent_bps=2_000)
        results = get_applicable_discounts(self.subscription, self.period, line_bases=self.bases)
        self.assertEqual([item.discount_id for item in results], [greater.pk, lower.pk, tied.pk])
        self.assertEqual(results[0].total_discount_paise, 5_000)

    def test_zero_saving_is_not_an_application(self):
        zero = self.make_rule(amount_paise=0, max_uses=1)
        self.assertEqual(get_applicable_discounts(self.subscription, self.period, line_bases=self.bases), [])
        zero.refresh_from_db()
        self.assertEqual(zero.used_count, 0)

    def test_reservation_is_guarded_against_exhausted_capacity(self):
        from core.services.pricing import DiscountApplication

        rule = self.make_rule(amount_paise=1_000, max_uses=1)
        invoice = Invoice.objects.create(
            number="INV-X", subscription=self.subscription, period_start=date(2024, 1, 1), period_end=date(2024, 2, 1),
            invoice_date=date(2024, 1, 1), due_date=date(2024, 1, 1), customer_name="Acme", customer_email="billing@example.test",
            subtotal_paise=25_000, discount_paise=0, tax_paise=0, total_paise=25_000,
        )
        application = DiscountApplication(rule.pk, rule.name, rule.kind, rule.amount_paise, None, (), 1_000)
        reserve_discount_usage(application, invoice)
        with self.assertRaises(DiscountCapacityChanged):
            reserve_discount_usage(application, invoice)
        rule.refresh_from_db()
        self.assertEqual(rule.used_count, 1)

    def test_billing_repeat_and_rule_edit_do_not_change_invoice_or_redemption_snapshot(self):
        admin = User.objects.create_user("admin-discount@example.test", "ValidPassword!", role=User.Role.ADMIN)
        rule = self.make_rule(name="Launch", amount_paise=1_000, max_uses=1)
        self.subscription.start_date = date(2024, 1, 1)
        self.subscription.billing_anchor_date = date(2024, 1, 1)
        self.subscription.next_invoice_date = date(2024, 1, 1)
        self.subscription.save()
        invoice = create_invoice_for_period(self.subscription.pk, date(2024, 1, 1), as_of=date(2024, 1, 1), actor=admin)
        again = create_invoice_for_period(self.subscription.pk, date(2024, 1, 1), as_of=date(2024, 1, 1), actor=admin)
        rule.refresh_from_db()
        rule.name = "Changed"
        rule.amount_paise = 5_000
        rule.save()
        snapshot = DiscountRedemption.objects.get(invoice=invoice)
        self.assertEqual(again.pk, invoice.pk)
        self.assertEqual(Invoice.objects.filter(subscription=self.subscription).count(), 1)
        self.assertEqual(snapshot.discount_name, "Launch")
        self.assertEqual(snapshot.value_paise, 1_000)
        self.assertEqual(snapshot.total_discount_paise, 1_000)
        self.assertEqual((invoice.subtotal_paise, invoice.discount_paise, invoice.tax_paise, invoice.total_paise), (25_000, 1_000, 0, 24_000))
        rule.refresh_from_db()
        self.assertEqual(rule.used_count, 1)


class DiscountAdminFormAndAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin-ui@example.test", "ValidPassword!", role=User.Role.ADMIN)
        self.staff = User.objects.create_user("staff-ui@example.test", "ValidPassword!", role=User.Role.STAFF)
        self.customer = User.objects.create_user("customer-ui@example.test", "ValidPassword!", role=User.Role.CUSTOMER)
        self.product = Product.objects.create(name="UI Product", type=Product.Type.SOFTWARE, sales_price_paise=100, cost_price_paise=0)

    def form_data(self, **updates):
        data = {
            "name": "Spring", "kind": Discount.Kind.FIXED, "scope": Discount.Scope.PRODUCTS,
            "amount_rupees": "12.34", "percent": "", "min_purchase_paise": "20.50", "min_quantity": "2",
            "starts_on": "2024-01-01", "ends_on": "2024-02-01", "max_uses": "1", "products": [str(self.product.pk)],
            "is_active": "on",
        }
        data.update(updates)
        return data

    def test_form_converts_currency_and_percent_exactly_and_validates_scope_and_limits(self):
        form = DiscountForm(self.form_data())
        self.assertTrue(form.is_valid(), form.errors)
        item = form.save()
        self.assertEqual(item.amount_paise, 1_234)
        self.assertEqual(item.min_purchase_paise, 2_050)
        self.assertEqual(list(item.products.all()), [self.product])
        invalid_scope = DiscountForm(self.form_data(products=[]))
        self.assertFalse(invalid_scope.is_valid())
        invalid_percent = DiscountForm(self.form_data(kind=Discount.Kind.PERCENT, amount_rupees="", percent="100.01"))
        self.assertFalse(invalid_percent.is_valid())
        percent_form = DiscountForm(self.form_data(kind=Discount.Kind.PERCENT, amount_rupees="", percent="12.34"))
        self.assertTrue(percent_form.is_valid(), percent_form.errors)
        self.assertEqual(percent_form.save().percent_bps, 1_234)

    def test_form_rejects_usage_limit_below_existing_redemptions(self):
        discount = Discount.objects.create(
            name="Used", kind=Discount.Kind.FIXED, amount_paise=100,
            scope=Discount.Scope.SUBSCRIPTION, starts_on=date(2024, 1, 1), max_uses=3, used_count=2,
        )
        data = self.form_data(scope=Discount.Scope.SUBSCRIPTION, products=[], max_uses="1")
        form = DiscountForm(data, instance=discount)
        self.assertFalse(form.is_valid())
        self.assertIn("max_uses", form.errors)

    def test_discount_crud_routes_require_admin(self):
        for user in (self.staff, self.customer):
            self.client.force_login(user)
            self.assertEqual(self.client.get("/offers/discounts/").status_code, 403)
            self.assertEqual(self.client.post("/offers/discounts/new/", self.form_data()).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/offers/discounts/").status_code, 200)
        response = self.client.post("/offers/discounts/new/", self.form_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Discount.objects.filter(name="Spring").count(), 1)
        discount = Discount.objects.get(name="Spring")
        for user in (self.staff, self.customer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(f"/offers/discounts/{discount.pk}/edit/").status_code, 403)
            self.assertEqual(self.client.post(f"/offers/discounts/{discount.pk}/archive/").status_code, 403)
        self.client.force_login(self.admin)
        discount.used_count = 1
        discount.save(update_fields=["used_count", "updated_at"])
        edit_data = self.form_data(name="Spring updated", max_uses="1")
        self.assertEqual(self.client.post(f"/offers/discounts/{discount.pk}/edit/", edit_data).status_code, 302)
        discount.refresh_from_db()
        self.assertEqual(discount.name, "Spring updated")
        self.assertEqual(discount.used_count, 1)
        self.assertEqual(self.client.get(f"/offers/discounts/{discount.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/offers/discounts/{discount.pk}/archive/").status_code, 405)
        self.assertEqual(self.client.post(f"/offers/discounts/{discount.pk}/archive/").status_code, 302)
        discount.refresh_from_db()
        self.assertFalse(discount.is_active)
