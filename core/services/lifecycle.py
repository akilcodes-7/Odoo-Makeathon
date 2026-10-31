"""The sole entry point for subscription and invoice state changes."""

from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.models import Invoice, Payment, Subscription, SubscriptionEvent
from core.services.exceptions import DomainValidationError
from core.services.dates import add_period, period_index_for_date


_SUBSCRIPTION_NEXT = {
    Subscription.Status.DRAFT: {Subscription.Status.QUOTATION, Subscription.Status.CLOSED},
    Subscription.Status.QUOTATION: {Subscription.Status.CONFIRMED, Subscription.Status.CLOSED},
    Subscription.Status.CONFIRMED: {Subscription.Status.ACTIVE, Subscription.Status.CLOSED},
    Subscription.Status.ACTIVE: {Subscription.Status.CLOSED},
    Subscription.Status.CLOSED: set(),
}


def _staff_actor(actor):
    if actor is not None and getattr(actor, "role", None) not in ("ADMIN", "STAFF"):
        raise PermissionDenied("Only staff can perform this internal action.")


def _customer_owns(subscription, actor):
    return (
        actor is not None
        and getattr(actor, "role", None) == "CUSTOMER"
        and subscription.customer.user_id == actor.pk
    )


def _validate_confirmable(subscription, today):
    if not subscription.plan.is_active:
        raise DomainValidationError("plan_archived", "The selected plan has been archived.")
    if not subscription.plan.primary_product.is_active:
        raise DomainValidationError("product_archived", "The plan's primary product has been archived.")
    if subscription.status == Subscription.Status.QUOTATION:
        if not subscription.quote_expires_on:
            raise DomainValidationError("quote_expiry_missing", "Set a quote expiry before confirming.")
        if subscription.quote_expires_on < today:
            raise DomainValidationError("quote_expired", "This quotation has expired.")
    lines = list(subscription.lines.select_related("product", "variant"))
    primaries = [line for line in lines if line.is_primary]
    if len(primaries) != 1 or primaries[0].product_id != subscription.plan.primary_product_id:
        raise DomainValidationError("primary_line_invalid", "Add exactly one primary line matching the plan.")
    if primaries[0].quantity < subscription.plan.min_quantity:
        raise DomainValidationError("minimum_quantity", "Primary line is below the plan's minimum quantity.")
    if any(line.quantity < 1 or line.unit_price_paise < 0 for line in lines):
        raise DomainValidationError("line_invalid", "Line quantities and prices must be valid.")
    for line in lines:
        if not line.product.is_active:
            raise DomainValidationError("line_product_archived", f"Product '{line.product.name}' on line {line.position} has been archived.")
        if line.variant_id and not line.variant.is_active:
            raise DomainValidationError("line_variant_archived", f"Variant on line {line.position} has been archived.")
        if line.variant_id and line.variant.product_id != line.product_id:
            raise DomainValidationError("variant_product_mismatch", "A selected variant does not belong to its product.")


def transition_subscription(subscription_id, target, *, actor, reason="", as_of=None):
    """Apply one legal status change and record its event atomically."""
    today = as_of or timezone.localdate()
    with transaction.atomic():
        subscription = Subscription.objects.select_for_update().select_related("plan", "plan__primary_product").get(pk=subscription_id)
        source = subscription.status
        if target not in _SUBSCRIPTION_NEXT.get(source, set()):
            raise DomainValidationError("invalid_transition", f"Cannot change {source} to {target}.")
        if target in (Subscription.Status.CONFIRMED, Subscription.Status.ACTIVE):
            _staff_actor(actor)
        if target == Subscription.Status.QUOTATION:
            _validate_confirmable(subscription, today)
            if not subscription.quote_expires_on:
                subscription.quote_expires_on = today + timedelta(days=7)
        elif target == Subscription.Status.CONFIRMED:
            _validate_confirmable(subscription, today)
            if subscription.plan.available_from and subscription.start_date < subscription.plan.available_from:
                raise DomainValidationError("plan_not_available", "The plan is not available on the contract start date.")
            if subscription.plan.available_until and subscription.start_date > subscription.plan.available_until:
                raise DomainValidationError("plan_not_available", "The plan is no longer available on the contract start date.")
            subscription.billing_period = subscription.plan.period
            subscription.auto_close_snapshot = subscription.plan.auto_close
            subscription.closable_snapshot = subscription.plan.closable
            subscription.pausable_snapshot = subscription.plan.pausable
            subscription.renewable_snapshot = subscription.plan.renewable
            subscription.min_quantity_snapshot = subscription.plan.min_quantity
        elif target == Subscription.Status.ACTIVE:
            if today < subscription.start_date:
                raise DomainValidationError("start_date_future", "A confirmed contract cannot activate before its start date.")
            subscription.billing_anchor_date = subscription.start_date
            subscription.billing_period_index = 0
            subscription.next_invoice_date = subscription.start_date
        elif target == Subscription.Status.CLOSED:
            if source == Subscription.Status.ACTIVE:
                if not _customer_owns(subscription, actor):
                    _staff_actor(actor)
                if not subscription.closable_snapshot:
                    raise DomainValidationError("not_closable", "This contract does not allow manual closure.")
                from core.services.billing import run_due_billing

                result = run_due_billing(as_of=today, subscription_ids=[subscription.pk], actor=actor)
                if result.errors or result.remaining_due_count:
                    detail = result.errors[0] if result.errors else "Due periods remain unbilled."
                    raise DomainValidationError("billing_incomplete", f"Bill due periods before closure: {detail}")
                subscription.refresh_from_db()
            subscription.closed_on = today
            subscription.closure_reason = reason.strip()
        subscription.status = target
        subscription.save()
        SubscriptionEvent.objects.create(
            subscription=subscription,
            actor=actor,
            action=SubscriptionEvent.Action.STATUS,
            from_status=source,
            to_status=target,
            note=reason.strip(),
        )
        return subscription


def finalize_expired_subscription(subscription_id, *, actor=None, as_of=None):
    """Close an auto-close contract after its last eligible period is settled."""
    today = as_of or timezone.localdate()
    with transaction.atomic():
        subscription = Subscription.objects.select_for_update().get(pk=subscription_id)
        if (
            subscription.status != Subscription.Status.ACTIVE
            or not subscription.auto_close_snapshot
            or subscription.expiry_date >= today
            or (subscription.next_invoice_date is not None and subscription.next_invoice_date <= subscription.expiry_date)
        ):
            return subscription
        source = subscription.status
        subscription.status = Subscription.Status.CLOSED
        subscription.closed_on = today
        subscription.closure_reason = "Automatically closed after final billable period."
        subscription.save(update_fields=["status", "closed_on", "closure_reason", "updated_at"])
        SubscriptionEvent.objects.create(
            subscription=subscription, actor=actor, action=SubscriptionEvent.Action.STATUS,
            from_status=source, to_status=Subscription.Status.CLOSED,
            note=subscription.closure_reason,
        )
        return subscription


def finalize_expired_paused_subscription(subscription_id, *, actor=None, as_of=None):
    """Close an expired paused auto-close contract without billing its paused interval."""
    today = as_of or timezone.localdate()
    with transaction.atomic():
        subscription = Subscription.objects.select_for_update().get(pk=subscription_id)
        if (
            subscription.status != Subscription.Status.ACTIVE
            or not subscription.is_paused
            or not subscription.auto_close_snapshot
            or subscription.expiry_date >= today
        ):
            return subscription
        source = subscription.status
        subscription.status = Subscription.Status.CLOSED
        subscription.closed_on = today
        subscription.is_paused = False
        subscription.pause_effective_on = None
        subscription.closure_reason = "Automatically closed after expiry (was paused)."
        subscription.save(update_fields=["status", "closed_on", "closure_reason", "is_paused", "pause_effective_on", "updated_at"])
        SubscriptionEvent.objects.create(
            subscription=subscription, actor=actor, action=SubscriptionEvent.Action.STATUS,
            from_status=source, to_status=Subscription.Status.CLOSED,
            note=subscription.closure_reason,
        )
        return subscription


def pause_subscription(subscription_id, *, actor, reason=""):
    today = timezone.localdate()
    with transaction.atomic():
        subscription = Subscription.objects.select_for_update().get(pk=subscription_id)
        if not _customer_owns(subscription, actor):
            _staff_actor(actor)
        if subscription.status != Subscription.Status.ACTIVE or not subscription.pausable_snapshot:
            raise DomainValidationError("pause_not_allowed", "This contract cannot be paused.")
        if subscription.is_paused or subscription.next_invoice_date is None:
            raise DomainValidationError("no_future_period", "There is no unpaid future period to pause.")
        from core.services.billing import run_due_billing

        result = run_due_billing(as_of=today, subscription_ids=[subscription.pk], actor=actor)
        if result.errors or result.remaining_due_count:
            raise DomainValidationError("billing_incomplete", "Due periods must be billed before pausing.")
        subscription.refresh_from_db()
        if subscription.next_invoice_date is None:
            raise DomainValidationError("no_future_period", "There is no unpaid future period to pause.")
        subscription.is_paused = True
        subscription.pause_effective_on = subscription.next_invoice_date
        subscription.save(update_fields=["is_paused", "pause_effective_on", "updated_at"])
        SubscriptionEvent.objects.create(
            subscription=subscription, actor=actor, action=SubscriptionEvent.Action.PAUSE,
            from_status=subscription.status, to_status=subscription.status, note=reason.strip(),
        )
        return subscription


def resume_subscription(subscription_id, *, actor, reason=""):
    today = timezone.localdate()
    with transaction.atomic():
        subscription = Subscription.objects.select_for_update().get(pk=subscription_id)
        if actor is not None and getattr(actor, "role", None) == "CUSTOMER":
            if not _customer_owns(subscription, actor):
                raise PermissionDenied
        else:
            _staff_actor(actor)
        if subscription.status != Subscription.Status.ACTIVE or not subscription.is_paused:
            raise DomainValidationError("not_paused", "This contract is not paused.")
        if today > subscription.expiry_date:
            raise DomainValidationError("contract_expired", "An expired contract cannot be resumed.")
        if subscription.pause_effective_on and today >= subscription.pause_effective_on:
            subscription.billing_anchor_date = today
            subscription.billing_period_index = 0
            subscription.next_invoice_date = today
        subscription.is_paused = False
        subscription.pause_effective_on = None
        subscription.save(update_fields=["billing_anchor_date", "billing_period_index", "next_invoice_date", "is_paused", "pause_effective_on", "updated_at"])
        SubscriptionEvent.objects.create(
            subscription=subscription, actor=actor, action=SubscriptionEvent.Action.RESUME,
            from_status=subscription.status, to_status=subscription.status, note=reason.strip(),
        )
        return subscription


def renewal_is_available(subscription, *, as_of=None):
    """Whether the closed, expired, or currently final-period contract can renew."""
    today = as_of or timezone.localdate()
    if not subscription.renewable_snapshot:
        return False
    if subscription.status == Subscription.Status.CLOSED:
        return True
    if subscription.status != Subscription.Status.ACTIVE:
        return False
    if today > subscription.expiry_date:
        return True
    if today < subscription.start_date:
        return False
    # Billing advances this cursor only after the period is invoiced. A
    # missing cursor or one beyond expiry therefore also proves the final
    # service period has already been billed, including advance billing.
    if subscription.next_invoice_date is None or subscription.next_invoice_date > subscription.expiry_date:
        return True
    final_index = period_index_for_date(
        subscription.billing_anchor_date,
        subscription.billing_period,
        subscription.expiry_date,
    )
    final_start = add_period(
        subscription.billing_anchor_date,
        subscription.billing_period,
        final_index,
    )
    return today >= final_start


def renew_subscription(subscription_id, *, actor, start_date=None, expiry_date=None):
    """Create or return the single independent draft successor."""
    from core.models import SubscriptionLine

    today = timezone.localdate()
    with transaction.atomic():
        original = Subscription.objects.select_for_update().select_related("plan", "customer").get(pk=subscription_id)
        if actor is not None and getattr(actor, "role", None) == "CUSTOMER":
            if original.customer.user_id != actor.pk:
                raise PermissionDenied
        else:
            _staff_actor(actor)
        if not original.renewable_snapshot:
            raise DomainValidationError("renewal_not_allowed", "This contract does not allow renewal.")
        existing = Subscription.objects.filter(renewed_from=original).first()
        if existing:
            return existing
        if not renewal_is_available(original, as_of=today):
            raise DomainValidationError("renewal_too_early", "Renewal is available after closure, expiry, or during the final service period.")
        if original.status == Subscription.Status.CLOSED and original.closed_on and original.closed_on < original.expiry_date:
            last_period_end = original.invoices.exclude(status=Invoice.Status.CANCELLED).aggregate(last=Max("period_end"))["last"]
            first_unpurchased_day = last_period_end or original.start_date
            default_start = max(today, first_unpurchased_day)
        else:
            default_start = max(today, original.expiry_date + timedelta(days=1))
        start = start_date or default_start
        if start < default_start:
            raise DomainValidationError("renewal_overlap", "Renewal cannot start before the current service term or purchased period ends.")
        end = expiry_date or (add_period(start, original.billing_period, 1) - timedelta(days=1))
        if end < start:
            raise DomainValidationError("renewal_dates_invalid", "Renewal expiry must be on or after its start.")
        draft = Subscription.objects.create(
            number="SUB-TEMP", customer=original.customer, plan=original.plan, renewed_from=original,
            status=Subscription.Status.DRAFT, start_date=start, expiry_date=end,
            payment_terms_days=original.payment_terms_days, quote_expires_on=None,
            billing_anchor_date=start, billing_period_index=0, next_invoice_date=None,
            billing_period=original.billing_period, auto_close_snapshot=original.auto_close_snapshot,
            closable_snapshot=original.closable_snapshot, pausable_snapshot=original.pausable_snapshot,
            renewable_snapshot=original.renewable_snapshot, min_quantity_snapshot=original.min_quantity_snapshot,
            created_by=actor,
        )
        draft.number = f"SUB-{draft.pk:06d}"
        draft.save(update_fields=["number", "updated_at"])
        for line in original.lines.all():
            copy = SubscriptionLine.objects.create(
                subscription=draft, product=line.product, variant=line.variant,
                is_primary=line.is_primary, description=line.description, quantity=line.quantity,
                unit_price_paise=line.unit_price_paise, position=line.position,
            )
            copy.taxes.set(line.taxes.all())
        SubscriptionEvent.objects.create(
            subscription=original, actor=actor, action=SubscriptionEvent.Action.RENEW,
            from_status=original.status, to_status=original.status, note=f"Renewal draft {draft.number} created.",
        )
        return draft


def transition_invoice(invoice_id, target, *, actor=None, reason=""):
    """Change invoice state; payment records remain the source of payment history."""
    _staff_actor(actor)
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
        allowed = {
            Invoice.Status.DRAFT: {Invoice.Status.CONFIRMED, Invoice.Status.CANCELLED},
            Invoice.Status.CONFIRMED: {Invoice.Status.PAID, Invoice.Status.CANCELLED},
            Invoice.Status.PAID: set(),
            Invoice.Status.CANCELLED: set(),
        }
        if target not in allowed[invoice.status]:
            raise DomainValidationError("invalid_invoice_transition", f"Cannot change {invoice.status} to {target}.")
        if target == Invoice.Status.CANCELLED and Payment.objects.filter(invoice=invoice).exists():
            raise DomainValidationError("invoice_has_payments", "An invoice with payments cannot be cancelled.")
        if target == Invoice.Status.PAID:
            if invoice.total_paise != 0:
                from core.services.finance import get_invoice_balance

                if get_invoice_balance(invoice.pk) != 0:
                    raise DomainValidationError("invoice_balance_due", "The invoice still has an outstanding balance.")
            if invoice.status != Invoice.Status.CONFIRMED:
                raise DomainValidationError("invoice_not_confirmed", "Only a confirmed invoice can be paid.")
        invoice.status = target
        invoice.save(update_fields=["status", "updated_at"])
        if target == Invoice.Status.CONFIRMED and invoice.total_paise == 0:
            invoice.status = Invoice.Status.PAID
            invoice.save(update_fields=["status", "updated_at"])
        return invoice
