from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from core.models import Customer, Plan, Product, Subscription, SubscriptionEvent, SubscriptionLine
from core.services.exceptions import DomainValidationError
from core.services.lifecycle import transition_subscription
from core.services.lifecycle import pause_subscription, renew_subscription, resume_subscription


class LifecycleServiceTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff@example.com", password="ValidPassword!", role=User.Role.STAFF)
        self.customer = Customer.objects.create(display_name="Acme", billing_email="acme@example.com")
        self.product = Product.objects.create(name="Cloud", type=Product.Type.SOFTWARE, sales_price_paise=12_500, cost_price_paise=4_000)
        self.plan = Plan.objects.create(
            name="Monthly", primary_product=self.product, price_paise=12_500,
            period=Plan.Period.MONTHLY, min_quantity=2, available_from=date(2020, 1, 1),
            renewable=True,
        )

    def make_draft(self, start=None):
        start = start or timezone.localdate()
        subscription = Subscription.objects.create(
            number="SUB-TEMP", customer=self.customer, plan=self.plan,
            status=Subscription.Status.DRAFT, start_date=start, expiry_date=start + timedelta(days=90),
            payment_terms_days=30, billing_anchor_date=start, billing_period_index=0,
            next_invoice_date=None, billing_period=Subscription.Period.MONTHLY,
        )
        subscription.number = f"SUB-{subscription.pk:06d}"
        subscription.save(update_fields=["number"])
        SubscriptionLine.objects.create(subscription=subscription, product=self.product, is_primary=True, quantity=2, unit_price_paise=12_500)
        return subscription

    def test_transition_path_records_events_and_snapshots_plan(self):
        subscription = self.make_draft()
        transition_subscription(subscription.pk, Subscription.Status.QUOTATION, actor=self.staff)
        transition_subscription(subscription.pk, Subscription.Status.CONFIRMED, actor=self.staff)
        self.plan.refresh_from_db()
        self.plan.min_quantity = 8
        self.plan.save()
        transition_subscription(subscription.pk, Subscription.Status.ACTIVE, actor=self.staff)
        subscription.refresh_from_db()
        self.assertEqual(subscription.min_quantity_snapshot, 2)
        self.assertEqual(subscription.next_invoice_date, subscription.start_date)
        self.assertEqual(subscription.events.count(), 3)
        self.assertEqual(subscription.events.first().to_status, Subscription.Status.ACTIVE)

    def test_skipping_or_reversing_status_is_rejected(self):
        subscription = self.make_draft()
        with self.assertRaises(DomainValidationError):
            transition_subscription(subscription.pk, Subscription.Status.ACTIVE, actor=self.staff)
        transition_subscription(subscription.pk, Subscription.Status.QUOTATION, actor=self.staff)
        with self.assertRaises(DomainValidationError):
            transition_subscription(subscription.pk, Subscription.Status.DRAFT, actor=self.staff)

    def test_future_contract_cannot_activate_early_and_min_quantity_is_enforced(self):
        future = timezone.localdate() + timedelta(days=4)
        subscription = self.make_draft(start=future)
        transition_subscription(subscription.pk, Subscription.Status.QUOTATION, actor=self.staff)
        transition_subscription(subscription.pk, Subscription.Status.CONFIRMED, actor=self.staff)
        with self.assertRaises(DomainValidationError):
            transition_subscription(subscription.pk, Subscription.Status.ACTIVE, actor=self.staff)

        too_small = self.make_draft()
        too_small.lines.update(quantity=1)
        with self.assertRaises(DomainValidationError):
            transition_subscription(too_small.pk, Subscription.Status.QUOTATION, actor=self.staff)

    def test_expired_quotation_cannot_be_confirmed(self):
        subscription = self.make_draft()
        transition_subscription(subscription.pk, Subscription.Status.QUOTATION, actor=self.staff)
        subscription.refresh_from_db()
        subscription.quote_expires_on = timezone.localdate() - timedelta(days=1)
        subscription.save(update_fields=["quote_expires_on"])
        with self.assertRaises(DomainValidationError):
            transition_subscription(subscription.pk, Subscription.Status.CONFIRMED, actor=self.staff)

    def make_active(self, number):
        today = timezone.localdate()
        self.plan.pausable = True
        self.plan.save(update_fields=["pausable"])
        subscription = Subscription.objects.create(
            number=number, customer=self.customer, plan=self.plan,
            status=Subscription.Status.ACTIVE, start_date=today,
            expiry_date=today + timedelta(days=180), payment_terms_days=0,
            billing_anchor_date=today, next_invoice_date=today,
            billing_period=Plan.Period.MONTHLY, closable_snapshot=True,
            pausable_snapshot=True, renewable_snapshot=True, min_quantity_snapshot=2,
        )
        SubscriptionLine.objects.create(subscription=subscription, product=self.product, is_primary=True, quantity=2, unit_price_paise=12_500)
        return subscription

    def test_pause_settles_due_period_and_resume_before_boundary_keeps_anchor(self):
        subscription = self.make_active("SUB-PAUSE")
        today = timezone.localdate()
        paused = pause_subscription(subscription.pk, actor=self.staff, reason="Test pause")
        self.assertTrue(paused.is_paused)
        self.assertEqual(paused.pause_effective_on, paused.next_invoice_date)
        self.assertEqual(paused.invoices.count(), 1)
        old_anchor = paused.billing_anchor_date
        resumed = resume_subscription(paused.pk, actor=self.staff, reason="Test resume")
        self.assertFalse(resumed.is_paused)
        self.assertEqual(resumed.billing_anchor_date, old_anchor)
        self.assertEqual(resumed.next_invoice_date, paused.pause_effective_on)
        self.assertEqual(today, resumed.start_date)

    def test_resume_after_pause_boundary_reanchors_and_renewal_is_idempotent(self):
        subscription = self.make_active("SUB-RENEW")
        paused = pause_subscription(subscription.pk, actor=self.staff)
        paused.pause_effective_on = timezone.localdate()
        paused.save(update_fields=["pause_effective_on"])
        resumed = resume_subscription(paused.pk, actor=self.staff)
        self.assertEqual(resumed.billing_anchor_date, timezone.localdate())
        self.assertEqual(resumed.billing_period_index, 0)
        closed = transition_subscription(resumed.pk, Subscription.Status.CLOSED, actor=self.staff)
        draft = renew_subscription(closed.pk, actor=self.staff)
        repeated = renew_subscription(closed.pk, actor=self.staff)
        self.assertEqual(draft.pk, repeated.pk)
        self.assertEqual(draft.status, Subscription.Status.DRAFT)
        self.assertEqual(draft.start_date, closed.invoices.order_by("-period_end").first().period_end)
        self.assertEqual(draft.lines.count(), closed.lines.count())
