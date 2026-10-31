"""Eligibility, allocation, and transactional reservation for discounts."""

from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from django.db.models import F, Q

from core.models import Discount
from core.services.exceptions import DiscountCapacityChanged
from core.services.pricing import BillingPeriod, DiscountApplication, LineBase

if TYPE_CHECKING:
    from core.models import Invoice, Subscription


def _allocate_fixed(total: int, lines: list[LineBase]) -> tuple[tuple[int, int], ...]:
    """Allocate paise proportionally using largest remainder, stable by line id."""
    subtotal = sum(line.subtotal_paise for line in lines)
    if total <= 0 or subtotal <= 0:
        return ()

    # Decimal keeps the proportional calculation exact and independent of floats.
    shares = {
        line.source_line_id: Decimal(total) * Decimal(line.subtotal_paise) / Decimal(subtotal)
        for line in lines
    }
    allocations = {line_id: int(share) for line_id, share in shares.items()}
    remainder = total - sum(allocations.values())
    rank = sorted(shares, key=lambda line_id: (-(shares[line_id] - allocations[line_id]), line_id))
    for line_id in rank[:remainder]:
        allocations[line_id] += 1
    return tuple(sorted((line_id, amount) for line_id, amount in allocations.items() if amount))


def _candidate(rule: Discount, bases: list[LineBase]) -> DiscountApplication | None:
    if rule.scope == Discount.Scope.PRODUCTS:
        selected_products = {product.pk for product in rule.products.all()}
        eligible = [base for base in bases if base.product_id in selected_products]
    else:
        eligible = list(bases)
    eligible_subtotal = sum(base.subtotal_paise for base in eligible)
    eligible_quantity = sum(base.quantity for base in eligible)
    if eligible_subtotal < rule.min_purchase_paise or eligible_quantity < rule.min_quantity:
        return None
    if not eligible:
        return None
    discounted_lines = [base for base in eligible if base.subtotal_paise > 0]
    if not discounted_lines:
        return None

    if rule.kind == Discount.Kind.FIXED:
        total = min(rule.amount_paise or 0, eligible_subtotal)
        allocations = _allocate_fixed(total, discounted_lines)
        value_paise, value_bps = rule.amount_paise, None
    else:
        allocations = tuple(
            (base.source_line_id, int((Decimal(base.subtotal_paise) * Decimal(rule.percent_bps or 0) / Decimal(10_000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
            for base in sorted(discounted_lines, key=lambda item: item.source_line_id)
        )
        allocations = tuple((line_id, amount) for line_id, amount in allocations if amount > 0)
        value_paise, value_bps = None, rule.percent_bps

    total = sum(amount for _, amount in allocations)
    if total <= 0:
        return None
    return DiscountApplication(
        discount_id=rule.pk,
        name=rule.name,
        kind=rule.kind,
        value_paise=value_paise,
        value_bps=value_bps,
        line_discounts=allocations,
        total_discount_paise=total,
    )


def get_applicable_discounts(
    subscription: "Subscription",
    period: BillingPeriod,
    *,
    line_bases: list[LineBase],
) -> list[DiscountApplication]:
    """Return saving-ranked eligible rules for this subscription period.

    Period-start dates are inclusive at both configured boundaries. Returning
    all candidates lets billing retry another rule if a guarded reservation
    loses a capacity race; the first candidate is the deterministic best rule.
    """
    del subscription  # Scope is encoded on each rule; the caller supplies this subscription's lines.
    rules = Discount.objects.filter(
        is_active=True,
        starts_on__lte=period.start,
    ).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=period.start))
    rules = rules.filter(scope=Discount.Scope.SUBSCRIPTION) | rules.filter(
        scope=Discount.Scope.PRODUCTS,
        products__in={base.product_id for base in line_bases},
    )
    rules = rules.filter(Q(max_uses__isnull=True) | Q(used_count__lt=F("max_uses")))
    rules = rules.distinct().prefetch_related("products")

    applications = []
    for rule in rules:
        application = _candidate(rule, line_bases)
        if application is not None:
            applications.append(application)
    return sorted(applications, key=lambda item: (-item.total_discount_paise, item.discount_id))

def reserve_discount_usage(application: DiscountApplication, invoice: "Invoice") -> None:
    """Atomically reserve one use; caller includes this in invoice transaction."""
    del invoice  # The invoice redemption snapshot is created by the billing owner.
    updated = Discount.objects.filter(pk=application.discount_id).filter(
        Q(max_uses__isnull=True) | Q(used_count__lt=F("max_uses"))
    ).update(used_count=F("used_count") + 1)
    if updated != 1:
        raise DiscountCapacityChanged("Discount capacity changed during invoice creation.")
