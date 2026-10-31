"""
Regression tests for A02, A03, A04, A01, A05, A06, A07, A08, A09, A10.

A01 — Stale draft save can overwrite a confirmed subscription
A02 — Tax edit silently halves the rate
A03 — Failed forms corrupt monetary/percentage inputs on redisplay
A04 — Product creation endpoint ignores POST data
A05 — Invalid plan IDs (non-integer) cause HTTP 500
A06 — Confirmation accepts archived catalog items
A07 — Renewal blocked during the final billing period
A08 — Paused auto-close contracts remain ACTIVE after expiry
A09 — One inconsistent cursor aborts the entire billing batch
A10 — Simulated future billing uses actual today for activation
"""

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from catalog.forms import ProductForm, TaxForm
from core.models import Product, Tax


# ---------------------------------------------------------------------------
# A02 — TaxForm initial value must not double-divide
# ---------------------------------------------------------------------------

class TaxFormInitialValueTests(TestCase):
    def test_edit_form_initial_rate_percent_is_18_00_for_1800_bps(self):
        """GET the edit form for a tax with rate_bps=1800; rendered value must be '18.00'."""
        tax = Tax.objects.create(name="GST", rate_bps=1800)
        form = TaxForm(instance=tax)
        rendered_value = form.fields["rate_percent"].prepare_value(
            form.fields["rate_percent"].initial
        )
        self.assertEqual(rendered_value, "18.00", f"Expected '18.00', got {rendered_value!r}")

    def test_post_unchanged_rate_stores_original_bps(self):
        """POST '18.00' back to the edit form; rate_bps must remain 1800."""
        tax = Tax.objects.create(name="GST", rate_bps=1800)
        form = TaxForm({"name": "GST", "rate_percent": "18.00"}, instance=tax)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.rate_bps, 1800)


# ---------------------------------------------------------------------------
# A03 — prepare_value must not divide on bound (string) redisplay
# ---------------------------------------------------------------------------

class BoundFormRedisplayTests(TestCase):
    """
    On a failed POST, Django calls prepare_value with the user's raw string
    (e.g. '560.00'), NOT the stored integer paise. Dividing again would
    show '5.60'.
    """

    def test_product_form_redisplay_shows_original_string_not_halved(self):
        """
        POST ProductForm with valid price but empty name → invalid.
        The redisplayed sales_price_paise value must be '560.00', not '5.60'.
        """
        form = ProductForm(
            {"name": "", "type": "SERVICE", "sales_price_paise": "560.00", "cost_price_paise": "0.00", "notes": ""}
        )
        self.assertFalse(form.is_valid())  # name is blank → should fail
        bf = form["sales_price_paise"]
        rendered = bf.value()
        self.assertEqual(rendered, "560.00", f"Expected '560.00' on redisplay, got {rendered!r}")

    def test_product_form_non_numeric_price_returns_200_not_500(self):
        """
        POST ProductForm with sales_price_paise='abc'.
        Must return a validation error, not an unhandled exception.
        """
        form = ProductForm(
            {"name": "Widget", "type": "SERVICE", "sales_price_paise": "abc", "cost_price_paise": "0.00", "notes": ""}
        )
        # is_valid() must not raise; it must return False with a field error
        self.assertFalse(form.is_valid())
        self.assertIn("sales_price_paise", form.errors)

    def test_discount_form_rupee_field_redisplay_unchanged(self):
        """
        POST a DiscountForm with amount_rupees='1000.00' and an invalid combination
        (kind=FIXED but also percent filled in). The redisplayed amount_rupees
        must be '1000.00', not '10.00'.
        """
        from offers.forms import DiscountForm
        from core.models import Discount
        form = DiscountForm({
            "name": "Test",
            "kind": Discount.Kind.FIXED,
            "scope": Discount.Scope.SUBSCRIPTION,
            "min_purchase_paise": "0.00",
            "min_quantity": "0",
            "starts_on": "2026-01-01",
            "amount_rupees": "1000.00",
            "percent": "10.00",   # invalid: both filled for FIXED
            "is_active": "on",
        })
        self.assertFalse(form.is_valid())
        rendered = form["amount_rupees"].value()
        self.assertEqual(rendered, "1000.00", f"Expected '1000.00' on redisplay, got {rendered!r}")


# ---------------------------------------------------------------------------
# A04 — product_create must bind POST data
# ---------------------------------------------------------------------------

class ProductCreateViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin@example.com", "pass", role=User.Role.ADMIN)
        self.staff = User.objects.create_user("staff@example.com", "pass", role=User.Role.STAFF)
        self.customer = User.objects.create_user("cust@example.com", "pass", role=User.Role.CUSTOMER)
        self.url = reverse("catalog:product_create")

    def test_admin_post_creates_product_with_correct_paise(self):
        """Admin POST with valid data → 302, one product row, correct paise stored."""
        client = Client()
        client.force_login(self.admin)
        response = client.post(self.url, {
            "name": "API Product",
            "type": "SERVICE",
            "sales_price_paise": "560.00",
            "cost_price_paise": "125.50",
            "notes": "",
        })
        self.assertEqual(response.status_code, 302, f"Expected 302 redirect, got {response.status_code}")
        self.assertEqual(Product.objects.count(), 1)
        p = Product.objects.get()
        self.assertEqual(p.sales_price_paise, 56000)
        self.assertEqual(p.cost_price_paise, 12550)

    def test_staff_post_is_denied_no_product_created(self):
        """Staff POST → 403 (or redirect), no product created."""
        client = Client()
        client.force_login(self.staff)
        response = client.post(self.url, {
            "name": "Staff Product",
            "type": "SERVICE",
            "sales_price_paise": "1.00",
            "cost_price_paise": "0",
            "notes": "",
        })
        self.assertIn(response.status_code, [302, 403])
        self.assertEqual(Product.objects.count(), 0)

    def test_customer_post_is_denied_no_product_created(self):
        """Customer POST → 403 (or redirect), no product created."""
        client = Client()
        client.force_login(self.customer)
        response = client.post(self.url, {
            "name": "Cust Product",
            "type": "SERVICE",
            "sales_price_paise": "1.00",
            "cost_price_paise": "0",
            "notes": "",
        })
        self.assertIn(response.status_code, [302, 403])
        self.assertEqual(Product.objects.count(), 0)


# ---------------------------------------------------------------------------
# Shared helpers for A01, A05, A06, A07, A08, A09, A10
# ---------------------------------------------------------------------------

from datetime import date, timedelta

from django.utils import timezone

from core.models import Customer, Plan, Product, Subscription, SubscriptionLine
from core.services.billing import run_due_billing
from core.services.exceptions import DomainValidationError
from core.services.lifecycle import (
    finalize_expired_paused_subscription,
    renew_subscription,
    transition_subscription,
)


def _make_staff():
    import uuid
    email = f"staff_{uuid.uuid4().hex[:8]}@example.com"
    return User.objects.create_user(email, password="ValidPassword!", role=User.Role.STAFF)


def _make_customer():
    return Customer.objects.create(display_name="Acme", billing_email="acme@example.com")


def _make_product(name="Cloud", is_active=True):
    p = Product.objects.create(
        name=name, type=Product.Type.SOFTWARE,
        sales_price_paise=12_500, cost_price_paise=4_000,
    )
    if not is_active:
        p.is_active = False
        p.save(update_fields=["is_active"])
    return p


def _make_plan(product, is_active=True, renewable=True):
    plan = Plan.objects.create(
        name="Monthly", primary_product=product, price_paise=12_500,
        period=Plan.Period.MONTHLY, min_quantity=1, available_from=date(2020, 1, 1),
        renewable=renewable, closable=True, auto_close=True,
    )
    if not is_active:
        plan.is_active = False
        plan.save(update_fields=["is_active"])
    return plan


def _make_draft(customer, plan, staff, start=None):
    today = start or timezone.localdate()
    sub = Subscription.objects.create(
        number="SUB-TEMP", customer=customer, plan=plan,
        status=Subscription.Status.DRAFT, start_date=today,
        expiry_date=today + timedelta(days=90),
        payment_terms_days=0, billing_anchor_date=today, billing_period_index=0,
        next_invoice_date=None, billing_period=Subscription.Period.MONTHLY,
    )
    sub.number = f"SUB-{sub.pk:06d}"
    sub.save(update_fields=["number"])
    SubscriptionLine.objects.create(
        subscription=sub, product=plan.primary_product,
        is_primary=True, quantity=2, unit_price_paise=12_500,
    )
    return sub


# ---------------------------------------------------------------------------
# A01 — Stale-draft race: locked subscription must reject save if confirmed
# ---------------------------------------------------------------------------

class A01StaleDraftSaveTests(TestCase):
    """
    Simulate the race: subscription is confirmed between the edit-form load
    and the POST. The view must detect the changed status via select_for_update
    and refuse the save.
    """

    def test_edit_post_is_rejected_when_subscription_no_longer_draft(self):
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        sub = _make_draft(customer, plan, staff)

        # Advance sub to CONFIRMED outside the view (simulate concurrent confirm)
        transition_subscription(sub.pk, Subscription.Status.QUOTATION, actor=staff)
        transition_subscription(sub.pk, Subscription.Status.CONFIRMED, actor=staff)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.CONFIRMED)

        # Now POST the edit view — status is no longer DRAFT
        client = Client()
        client.force_login(staff)
        url = reverse("subscriptions:edit", args=[sub.pk])
        response = client.post(url, {
            "customer": customer.pk,
            "plan": plan.pk,
            "start_date": sub.start_date.isoformat(),
            "expiry_date": sub.expiry_date.isoformat(),
            "payment_terms_days": 0,
        })
        # Should redirect (the locked guard fires and redirects to detail)
        self.assertIn(response.status_code, [302, 200])
        sub.refresh_from_db()
        # Status must still be CONFIRMED — not reverted to DRAFT
        self.assertEqual(sub.status, Subscription.Status.CONFIRMED)


# ---------------------------------------------------------------------------
# A05 — Non-integer plan_id must not raise 500
# ---------------------------------------------------------------------------

class A05InvalidPlanIdTests(TestCase):
    def test_create_view_with_non_integer_plan_id_returns_200_not_500(self):
        staff = _make_staff()
        client = Client()
        client.force_login(staff)
        url = reverse("subscriptions:new")
        response = client.get(url + "?plan=abc")
        self.assertEqual(response.status_code, 200)

    def test_edit_view_with_non_integer_plan_id_in_post_does_not_raise(self):
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        sub = _make_draft(customer, plan, staff)

        client = Client()
        client.force_login(staff)
        url = reverse("subscriptions:edit", args=[sub.pk])
        # plan=abc is non-integer; must not 500
        response = client.post(url, {
            "customer": customer.pk,
            "plan": "abc",
            "start_date": sub.start_date.isoformat(),
            "expiry_date": sub.expiry_date.isoformat(),
            "payment_terms_days": 0,
        })
        self.assertNotEqual(response.status_code, 500)


# ---------------------------------------------------------------------------
# A06 — Archived plan or product must block confirmation
# ---------------------------------------------------------------------------

class A06ArchivedCatalogItemTests(TestCase):
    def test_archived_plan_blocks_quotation_transition(self):
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        sub = _make_draft(customer, plan, staff)

        plan.is_active = False
        plan.save(update_fields=["is_active"])

        with self.assertRaises(DomainValidationError) as ctx:
            transition_subscription(sub.pk, Subscription.Status.QUOTATION, actor=staff)
        self.assertEqual(ctx.exception.code, "plan_archived")

    def test_archived_primary_product_blocks_quotation_transition(self):
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        sub = _make_draft(customer, plan, staff)

        product.is_active = False
        product.save(update_fields=["is_active"])

        with self.assertRaises(DomainValidationError) as ctx:
            transition_subscription(sub.pk, Subscription.Status.QUOTATION, actor=staff)
        self.assertEqual(ctx.exception.code, "product_archived")

    def test_archived_line_product_blocks_quotation_transition(self):
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        sub = _make_draft(customer, plan, staff)

        # Add an extra non-primary line with an archived product
        extra_product = _make_product(name="Addon")
        SubscriptionLine.objects.create(
            subscription=sub, product=extra_product,
            is_primary=False, quantity=1, unit_price_paise=500,
        )
        extra_product.is_active = False
        extra_product.save(update_fields=["is_active"])

        with self.assertRaises(DomainValidationError) as ctx:
            transition_subscription(sub.pk, Subscription.Status.QUOTATION, actor=staff)
        self.assertEqual(ctx.exception.code, "line_product_archived")

    def test_active_plan_and_products_allow_confirmation(self):
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        sub = _make_draft(customer, plan, staff)
        # Should succeed
        result = transition_subscription(sub.pk, Subscription.Status.QUOTATION, actor=staff)
        self.assertEqual(result.status, Subscription.Status.QUOTATION)


# ---------------------------------------------------------------------------
# A07 — Renewal allowed in final billing period
# ---------------------------------------------------------------------------

class A07FinalPeriodRenewalTests(TestCase):
    def test_renewal_allowed_when_next_invoice_date_is_none(self):
        """next_invoice_date=None means all periods billed — final period."""
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product, renewable=True)
        today = timezone.localdate()
        sub = Subscription.objects.create(
            number="SUB-000099", customer=customer, plan=plan,
            status=Subscription.Status.ACTIVE,
            start_date=today - timedelta(days=60),
            expiry_date=today + timedelta(days=5),  # not yet expired
            payment_terms_days=0,
            billing_anchor_date=today - timedelta(days=60),
            billing_period_index=2, next_invoice_date=None,  # all billed
            billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=True, closable_snapshot=True,
            pausable_snapshot=False, renewable_snapshot=True, min_quantity_snapshot=1,
        )
        SubscriptionLine.objects.create(
            subscription=sub, product=product,
            is_primary=True, quantity=1, unit_price_paise=12_500,
        )
        # Must NOT raise renewal_too_early
        draft = renew_subscription(sub.pk, actor=staff)
        self.assertEqual(draft.status, Subscription.Status.DRAFT)

    def test_renewal_allowed_when_next_invoice_date_past_expiry(self):
        """next_invoice_date > expiry_date means in final period."""
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product, renewable=True)
        today = timezone.localdate()
        expiry = today + timedelta(days=5)
        sub = Subscription.objects.create(
            number="SUB-000100", customer=customer, plan=plan,
            status=Subscription.Status.ACTIVE,
            start_date=today - timedelta(days=60),
            expiry_date=expiry,
            payment_terms_days=0,
            billing_anchor_date=today - timedelta(days=60),
            billing_period_index=2,
            next_invoice_date=expiry + timedelta(days=1),  # past expiry → final
            billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=True, closable_snapshot=True,
            pausable_snapshot=False, renewable_snapshot=True, min_quantity_snapshot=1,
        )
        SubscriptionLine.objects.create(
            subscription=sub, product=product,
            is_primary=True, quantity=1, unit_price_paise=12_500,
        )
        draft = renew_subscription(sub.pk, actor=staff)
        self.assertEqual(draft.status, Subscription.Status.DRAFT)

    def test_renewal_blocked_when_not_in_final_period(self):
        """next_invoice_date < expiry_date and not CLOSED → too early."""
        staff = _make_staff()
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product, renewable=True)
        today = timezone.localdate()
        expiry = today + timedelta(days=30)
        sub = Subscription.objects.create(
            number="SUB-000101", customer=customer, plan=plan,
            status=Subscription.Status.ACTIVE,
            start_date=today - timedelta(days=30),
            expiry_date=expiry,
            payment_terms_days=0,
            billing_anchor_date=today - timedelta(days=30),
            billing_period_index=1,
            next_invoice_date=today + timedelta(days=1),  # next period within term
            billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=True, closable_snapshot=True,
            pausable_snapshot=False, renewable_snapshot=True, min_quantity_snapshot=1,
        )
        SubscriptionLine.objects.create(
            subscription=sub, product=product,
            is_primary=True, quantity=1, unit_price_paise=12_500,
        )
        with self.assertRaises(DomainValidationError) as ctx:
            renew_subscription(sub.pk, actor=staff)
        self.assertEqual(ctx.exception.code, "renewal_too_early")


# ---------------------------------------------------------------------------
# A08 — Paused auto-close subscription is closed after expiry
# ---------------------------------------------------------------------------

class A08PausedAutoCloseTests(TestCase):
    def test_finalize_expired_paused_subscription_closes_it(self):
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        sub = Subscription.objects.create(
            number="SUB-PAUSED", customer=customer, plan=plan,
            status=Subscription.Status.ACTIVE,
            start_date=yesterday - timedelta(days=30),
            expiry_date=yesterday,
            payment_terms_days=0,
            billing_anchor_date=yesterday - timedelta(days=30),
            billing_period_index=1, next_invoice_date=yesterday,
            billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=True, closable_snapshot=True,
            pausable_snapshot=True, renewable_snapshot=True, min_quantity_snapshot=1,
            is_paused=True, pause_effective_on=yesterday,
        )
        SubscriptionLine.objects.create(
            subscription=sub, product=product,
            is_primary=True, quantity=1, unit_price_paise=12_500,
        )
        result = finalize_expired_paused_subscription(sub.pk, as_of=today)
        self.assertEqual(result.status, Subscription.Status.CLOSED)
        self.assertFalse(result.is_paused)
        self.assertEqual(result.closed_on, today)

    def test_run_due_billing_closes_expired_paused_auto_close_subscription(self):
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        sub = Subscription.objects.create(
            number="SUB-PEXP", customer=customer, plan=plan,
            status=Subscription.Status.ACTIVE,
            start_date=yesterday - timedelta(days=30),
            expiry_date=yesterday,
            payment_terms_days=0,
            billing_anchor_date=yesterday - timedelta(days=30),
            billing_period_index=1, next_invoice_date=yesterday,
            billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=True, closable_snapshot=True,
            pausable_snapshot=True, renewable_snapshot=True, min_quantity_snapshot=1,
            is_paused=True, pause_effective_on=yesterday,
        )
        SubscriptionLine.objects.create(
            subscription=sub, product=product,
            is_primary=True, quantity=1, unit_price_paise=12_500,
        )
        result = run_due_billing(as_of=today, subscription_ids=[sub.pk])
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.CLOSED)
        self.assertEqual(result.errors, ())

    def test_non_paused_expired_sub_is_unaffected_by_paused_finalizer(self):
        """finalize_expired_paused_subscription is a no-op for non-paused subs."""
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        sub = Subscription.objects.create(
            number="SUB-NONP", customer=customer, plan=plan,
            status=Subscription.Status.ACTIVE,
            start_date=yesterday - timedelta(days=30),
            expiry_date=yesterday,
            payment_terms_days=0,
            billing_anchor_date=yesterday - timedelta(days=30),
            billing_period_index=1, next_invoice_date=None,
            billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=True, closable_snapshot=True,
            pausable_snapshot=False, renewable_snapshot=True, min_quantity_snapshot=1,
            is_paused=False,
        )
        SubscriptionLine.objects.create(
            subscription=sub, product=product,
            is_primary=True, quantity=1, unit_price_paise=12_500,
        )
        result = finalize_expired_paused_subscription(sub.pk, as_of=today)
        # Not paused → guard exits, status unchanged
        self.assertEqual(result.status, Subscription.Status.ACTIVE)


# ---------------------------------------------------------------------------
# A09 — Inconsistent cursor must not abort the entire billing batch
# ---------------------------------------------------------------------------

class A09InconsistentCursorTests(TestCase):
    def test_cursor_mismatch_records_error_and_continues_to_next_subscription(self):
        """A subscription with a corrupt cursor emits an error but the batch continues."""
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        today = timezone.localdate()
        start = date(2024, 1, 31)
        expiry = date(2024, 5, 30)

        # Good subscription — should be billed normally
        good = Subscription.objects.create(
            number="SUB-GOOD", customer=customer, plan=plan,
            status=Subscription.Status.ACTIVE, start_date=start, expiry_date=expiry,
            payment_terms_days=0, billing_anchor_date=start, billing_period_index=0,
            next_invoice_date=start, billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=False, closable_snapshot=True,
            pausable_snapshot=False, renewable_snapshot=True, min_quantity_snapshot=1,
        )
        SubscriptionLine.objects.create(
            subscription=good, product=product, is_primary=True,
            quantity=1, unit_price_paise=12_500,
        )

        # Bad subscription — cursor disagrees with anchor+index (next_invoice_date is wrong)
        bad = Subscription.objects.create(
            number="SUB-BAD", customer=customer, plan=plan,
            status=Subscription.Status.ACTIVE, start_date=start, expiry_date=expiry,
            payment_terms_days=0, billing_anchor_date=start, billing_period_index=0,
            next_invoice_date=start + timedelta(days=1),  # cursor differs by 1 day from period.start
            billing_period=Subscription.Period.MONTHLY,
            auto_close_snapshot=False, closable_snapshot=True,
            pausable_snapshot=False, renewable_snapshot=True, min_quantity_snapshot=1,
        )
        SubscriptionLine.objects.create(
            subscription=bad, product=product, is_primary=True,
            quantity=1, unit_price_paise=12_500,
        )

        result = run_due_billing(
            as_of=date(2024, 2, 29),
            subscription_ids=[good.pk, bad.pk],
            max_periods_per_subscription=1,
        )
        # Good sub must have produced an invoice
        self.assertEqual(len(result.created_ids), 1)
        # Bad sub must have contributed exactly one error, not crashed everything
        self.assertEqual(len(result.errors), 1)
        self.assertIn("SUB-BAD", result.errors[0])


# ---------------------------------------------------------------------------
# A10 — Simulated future billing activates CONFIRMED subscription via as_of
# ---------------------------------------------------------------------------

class A10FutureBillingActivationTests(TestCase):
    def test_confirmed_subscription_is_activated_when_as_of_reaches_start_date(self):
        """
        With as_of = start_date (future), transition_subscription must use as_of,
        not real today, so start_date_future guard passes.
        """
        customer = _make_customer()
        product = _make_product()
        plan = _make_plan(product)
        staff = _make_staff()

        future_start = timezone.localdate() + timedelta(days=30)
        sub = _make_draft(customer, plan, staff, start=future_start)
        sub.expiry_date = future_start + timedelta(days=90)
        sub.save(update_fields=["expiry_date"])

        transition_subscription(sub.pk, Subscription.Status.QUOTATION, actor=staff)
        transition_subscription(sub.pk, Subscription.Status.CONFIRMED, actor=staff)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.CONFIRMED)

        # Simulate billing run as_of future_start — must activate without error
        result = run_due_billing(as_of=future_start, subscription_ids=[sub.pk])
        self.assertEqual(result.errors, (), f"Unexpected errors: {result.errors}")
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)
