"""Add evaluator scenarios using the same lifecycle and payment services as the UI."""

from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from core.management.commands.seed_demo import Command as SeedDemoCommand
from core.models import Customer, Invoice, Payment, Plan, Subscription, SubscriptionLine, Tax
from core.services.billing import run_due_billing
from core.services.lifecycle import pause_subscription, transition_invoice, transition_subscription
from finance.services.payments import record_payment


class Command(SeedDemoCommand):
    help = "Create demo accounts and a complete local evaluator walkthrough dataset."

    def _seed_data(self, users):
        super()._seed_data(users)
        today = timezone.localdate()
        staff = users["staff@brightloop.test"]
        customer = Customer.objects.get(user=users["customer@brightloop.test"])
        other = Customer.objects.get(user=users["customer2@brightloop.test"])
        plan = Plan.objects.get(name="Professional Monthly")
        tax = Tax.objects.get(name="GST 18%")

        scenarios = (
            ("EVAL-READY", customer, today, today + timedelta(days=60), "DRAFT"),
            ("EVAL-BILLING", other, today, today + timedelta(days=60), "CONFIRMED"),
            ("EVAL-PARTIAL", customer, today - timedelta(days=10), today + timedelta(days=80), "PARTIAL"),
            ("EVAL-RENEW", other, today - timedelta(days=20), today + timedelta(days=5), "RENEW"),
            ("EVAL-PAUSE", customer, today - timedelta(days=10), today + timedelta(days=80), "PAUSE"),
        )
        for number, owner, start, expiry, scenario in scenarios:
            # Fixed identifiers retain the evaluator's subsequent changes.
            if Subscription.objects.filter(number=number).exists():
                continue
            subscription = Subscription.objects.create(
                number=number, customer=owner, plan=plan, start_date=start, expiry_date=expiry,
                billing_anchor_date=start, billing_period=plan.period, payment_terms_days=7,
                quote_expires_on=today + timedelta(days=14), created_by=staff,
            )
            line = SubscriptionLine.objects.create(
                subscription=subscription, product=plan.primary_product, is_primary=True,
                quantity=1, unit_price_paise=plan.price_paise, position=0,
            )
            line.taxes.add(tax)
            if scenario == "DRAFT":
                continue
            transition_subscription(subscription.pk, Subscription.Status.QUOTATION, actor=staff)
            transition_subscription(subscription.pk, Subscription.Status.CONFIRMED, actor=staff)
            if scenario == "CONFIRMED":
                continue
            transition_subscription(subscription.pk, Subscription.Status.ACTIVE, actor=staff)
            result = run_due_billing(as_of=today, subscription_ids=[subscription.pk], actor=staff)
            if result.errors:
                raise ValueError("Evaluator fixture billing failed: " + "; ".join(result.errors))
            for invoice in subscription.invoices.all():
                transition_invoice(invoice.pk, Invoice.Status.CONFIRMED, actor=staff)
                if scenario == "PARTIAL":
                    record_payment(
                        invoice.pk, amount_paise=invoice.total_paise // 2,
                        method=Payment.Method.BANK, paid_on=today,
                        note="Evaluator example: partial payment; record the remaining balance in the UI.",
                        idempotency_key=uuid4(), actor=staff,
                    )
            if scenario == "PAUSE":
                pause_subscription(subscription.pk, actor=staff, reason="Evaluator example: pause scheduled after the purchased period.")
