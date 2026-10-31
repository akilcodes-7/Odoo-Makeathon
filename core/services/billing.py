"""Transactional recurring invoice creation and bounded catch-up."""

from datetime import date, timedelta
import time

from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F

from core.models import (
    DiscountRedemption, Invoice, InvoiceLine, InvoiceLineTax, Subscription,
)
from core.services.dates import period_for_index
from core.services.exceptions import DiscountCapacityChanged, DomainValidationError
from core.services.money import prorate_paise, tax_paise
from core.services.pricing import BillingPeriod, BillingResult, LineBase, TaxSnapshot


def _invoice_number(invoice):
    invoice.number = f"INV-{invoice.pk:06d}"
    invoice.save(update_fields=["number", "updated_at"])


def _period_from_cursor(subscription):
    if subscription.next_invoice_date is None:
        return None
    period = period_for_index(
        subscription.billing_anchor_date,
        subscription.billing_period,
        subscription.billing_period_index,
        subscription.expiry_date,
    )
    if period and period.start != subscription.next_invoice_date:
        raise DomainValidationError(
            "billing_cursor_inconsistent",
            "The billing cursor does not match its anchor and period index; no invoice was created.",
        )
    return period


def _line_bases(subscription, period: BillingPeriod):
    bases = []
    for line in subscription.lines.select_related("product", "variant").prefetch_related("taxes"):
        subtotal = prorate_paise(
            line.unit_price_paise * line.quantity,
            period.actual_days,
            period.nominal_days,
        )
        taxes = tuple(
            TaxSnapshot(tax_id=tax.pk, name=tax.name, rate_bps=tax.rate_bps)
            for tax in sorted(line.taxes.all(), key=lambda tax: tax.pk)
        )
        bases.append(LineBase(
            source_line_id=line.pk,
            product_id=line.product_id,
            quantity=line.quantity,
            unit_price_paise=line.unit_price_paise,
            subtotal_paise=subtotal,
            taxes=taxes,
        ))
    return bases


def create_invoice_for_period(subscription_id, period_start: date, *, as_of: date, actor=None) -> Invoice:
    """Create one invoice and advance its subscription cursor atomically."""
    from offers.services.discounts import get_applicable_discounts, reserve_discount_usage

    try:
        with transaction.atomic():
            subscription = (
                Subscription.objects.select_for_update()
                .select_related("customer", "customer__user", "plan")
                .get(pk=subscription_id)
            )
            if subscription.status != Subscription.Status.ACTIVE or subscription.is_paused:
                raise DomainValidationError("subscription_not_billable", "This subscription is not billable now.")
            if subscription.closed_on or subscription.start_date > as_of or subscription.expiry_date < period_start:
                raise DomainValidationError("subscription_outside_term", "This subscription has no eligible period.")
            period = _period_from_cursor(subscription)
            if period is None or period.start != period_start:
                existing = Invoice.objects.filter(subscription=subscription, period_start=period_start).first()
                if existing:
                    return existing
                raise DomainValidationError("period_not_current", "Requested period does not match the billing cursor.")
            if period.start > as_of:
                raise DomainValidationError("period_not_due", "This billing period is not due yet.")
            existing = Invoice.objects.filter(subscription=subscription, period_start=period.start).first()
            if existing:
                subscription.next_invoice_date = existing.period_end
                subscription.billing_period_index += 1
                subscription.save(update_fields=["next_invoice_date", "billing_period_index", "updated_at"])
                return existing

            bases = _line_bases(subscription, period)
            if not bases:
                raise DomainValidationError("subscription_lines_missing", "A billable subscription needs at least one line.")
            candidates = get_applicable_discounts(subscription, period, line_bases=bases)
            # Teammate 1 returns candidates sorted by deterministic preference.
            application = candidates[0] if candidates else None
            discounts = dict(application.line_discounts) if application else {}
            # Reject malformed allocations before they reach constrained invoice rows.
            base_by_id = {base.source_line_id: base for base in bases}
            for line_id, amount in discounts.items():
                if line_id not in base_by_id or amount < 0 or amount > base_by_id[line_id].subtotal_paise:
                    raise DomainValidationError("discount_allocation_invalid", "The selected discount allocation is invalid.")
            discount_total = sum(discounts.values())
            if application and discount_total != application.total_discount_paise:
                raise DomainValidationError("discount_total_invalid", "The selected discount total does not reconcile.")

            line_calculations = {}
            tax_total = 0
            invoice_total = 0
            for base in bases:
                line_discount = discounts.get(base.source_line_id, 0)
                taxable = base.subtotal_paise - line_discount
                tax_amounts = tuple((tax, tax_paise(taxable, tax.rate_bps)) for tax in base.taxes)
                line_tax = sum(amount for _tax, amount in tax_amounts)
                line_calculations[base.source_line_id] = (line_discount, taxable, tax_amounts, line_tax)
                tax_total += line_tax
                invoice_total += taxable + line_tax

            invoice = Invoice.objects.create(
                number="INV-TEMP",
                subscription=subscription,
                period_start=period.start,
                period_end=period.end,
                invoice_date=period.start,
                due_date=period.start + timedelta(days=subscription.payment_terms_days),
                status=Invoice.Status.DRAFT,
                customer_name=subscription.customer.display_name,
                customer_email=subscription.customer.billing_email,
                customer_address=subscription.customer.billing_address,
                currency="INR",
                subtotal_paise=sum(base.subtotal_paise for base in bases),
                discount_paise=discount_total,
                tax_paise=tax_total,
                total_paise=invoice_total,
                terms_days_snapshot=subscription.payment_terms_days,
                created_by=actor,
            )
            _invoice_number(invoice)
            for position, base in enumerate(bases):
                source = subscription.lines.get(pk=base.source_line_id)
                line_discount, taxable, tax_amounts, line_tax = line_calculations[base.source_line_id]
                line = InvoiceLine.objects.create(
                    invoice=invoice,
                    source_line=source,
                    product_name=source.product.name,
                    variant_description=(f"{source.variant.attribute_name}: {source.variant.attribute_value}" if source.variant_id else ""),
                    quantity=base.quantity,
                    unit_price_paise=base.unit_price_paise,
                    period_numerator_days=period.actual_days,
                    period_denominator_days=period.nominal_days,
                    subtotal_paise=base.subtotal_paise,
                    discount_paise=line_discount,
                    taxable_paise=taxable,
                    tax_paise=line_tax,
                    total_paise=taxable + line_tax,
                    position=position,
                )
                for tax, amount in tax_amounts:
                    InvoiceLineTax.objects.create(
                        invoice_line=line,
                        source_tax_id=tax.tax_id,
                        tax_name=tax.name,
                        rate_bps=tax.rate_bps,
                        amount_paise=amount,
                    )
            if application and discount_total > 0:
                reserve_discount_usage(application, invoice)
                DiscountRedemption.objects.create(
                    invoice=invoice,
                    discount_id=application.discount_id,
                    discount_name=application.name,
                    kind=application.kind,
                    value_paise=application.value_paise,
                    value_bps=application.value_bps,
                    total_discount_paise=discount_total,
                )
            subscription.billing_period_index += 1
            next_period = period_for_index(
                subscription.billing_anchor_date,
                subscription.billing_period,
                subscription.billing_period_index,
                subscription.expiry_date,
            )
            subscription.next_invoice_date = next_period.start if next_period else None
            subscription.save(update_fields=["billing_period_index", "next_invoice_date", "updated_at"])
            return invoice
    except IntegrityError:
        # The failed savepoint has been exited; uniqueness is authoritative.
        existing = Invoice.objects.filter(subscription_id=subscription_id, period_start=period_start).first()
        if existing:
            return existing
        raise


def _one_period(subscription_id, as_of, actor):
    for attempt in range(3):
        try:
            subscription = Subscription.objects.get(pk=subscription_id)
            period = _period_from_cursor(subscription)
            if period is None or period.start > as_of:
                return None, None, False
            existed = Invoice.objects.filter(subscription_id=subscription_id, period_start=period.start).exists()
            invoice = create_invoice_for_period(subscription_id, period.start, as_of=as_of, actor=actor)
            return invoice, None, existed
        except DiscountCapacityChanged:
            if attempt == 2:
                return None, "Discount capacity changed repeatedly; retry this period later.", False
            time.sleep(0.05 * (attempt + 1))
        except OperationalError as exc:
            if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                return None, str(exc), False
            if attempt == 2:
                return None, "Database remained busy after three billing attempts.", False
            time.sleep(0.05 * (attempt + 1))
        except Exception as exc:
            return None, str(exc), False
    return None, "Billing retry limit reached.", False


def run_due_billing(*, as_of: date, subscription_ids=None, max_periods_per_subscription=24, actor=None) -> BillingResult:
    """Run a bounded batch, retaining every unprocessed cursor for the next run."""
    from core.services.lifecycle import finalize_expired_subscription, transition_subscription

    if max_periods_per_subscription < 1:
        raise ValueError("max_periods_per_subscription must be positive.")
    queryset = Subscription.objects.filter(
        status__in=[Subscription.Status.CONFIRMED, Subscription.Status.ACTIVE],
        start_date__lte=as_of,
    )
    queryset = queryset.exclude(expiry_date__lt=F("start_date"))
    if subscription_ids is not None:
        queryset = queryset.filter(pk__in=subscription_ids)
    created, existing, errors = [], [], []
    for sub_id in queryset.order_by("pk").values_list("pk", flat=True).iterator():
        sub = Subscription.objects.get(pk=sub_id)
        try:
            if sub.status == Subscription.Status.CONFIRMED:
                transition_subscription(sub_id, Subscription.Status.ACTIVE, actor=actor, reason="Activated by due billing run.")
        except Exception as exc:
            errors.append(f"{sub.number}: {exc}")
            continue
        for _ in range(max_periods_per_subscription):
            current = Subscription.objects.get(pk=sub_id)
            if current.is_paused or current.next_invoice_date is None or current.next_invoice_date > as_of:
                break
            period = _period_from_cursor(current)
            if period is None:
                current.next_invoice_date = None
                current.save(update_fields=["next_invoice_date", "updated_at"])
                break
            invoice, error, existed = _one_period(sub_id, as_of, actor)
            if error:
                errors.append(f"{current.number}: {error}")
                break
            if invoice:
                (existing if existed else created).append(invoice.pk)
    remaining_query = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        is_paused=False,
        next_invoice_date__lte=as_of,
    ).exclude(expiry_date__lt=F("next_invoice_date"))
    if subscription_ids is not None:
        remaining_query = remaining_query.filter(pk__in=subscription_ids)
    remaining = remaining_query.count()
    # Expiry finalization also covers subscriptions whose final period has
    # already advanced the cursor to None, or which were paused at expiry.
    expiry_ids = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        auto_close_snapshot=True,
        expiry_date__lt=as_of,
        is_paused=False,
    ).values_list("pk", flat=True)
    if subscription_ids is not None:
        expiry_ids = expiry_ids.filter(pk__in=subscription_ids)
    for sub_id in expiry_ids:
        current = Subscription.objects.get(pk=sub_id)
        try:
            finalize_expired_subscription(sub_id, actor=actor, as_of=as_of)
        except Exception as exc:
            errors.append(f"{current.number}: auto-close failed: {exc}")
    return BillingResult(
        created_ids=tuple(created), existing_ids=tuple(existing), errors=tuple(errors),
        remaining_due_count=remaining,
    )
