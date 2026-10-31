"""Calendar-safe recurring billing dates."""

from calendar import monthrange
from datetime import date, timedelta

from core.models import Subscription
from core.services.pricing import BillingPeriod


def add_period(anchor: date, period: str, index: int = 1) -> date:
    """Return a boundary from the original anchor, preserving month-end intent."""
    if index < 0:
        raise ValueError("Period index cannot be negative.")
    if period == Subscription.Period.DAILY:
        return anchor + timedelta(days=index)
    if period == Subscription.Period.WEEKLY:
        return anchor + timedelta(days=7 * index)
    if period in (Subscription.Period.MONTHLY, Subscription.Period.YEARLY):
        months = index if period == Subscription.Period.MONTHLY else 12 * index
        absolute_month = anchor.year * 12 + anchor.month - 1 + months
        year, month0 = divmod(absolute_month, 12)
        month = month0 + 1
        day = min(anchor.day, monthrange(year, month)[1])
        return date(year, month, day)
    raise ValueError(f"Unsupported billing period: {period}")


def period_for_index(anchor: date, period: str, index: int, expiry: date) -> BillingPeriod | None:
    """Build the half-open period at index, clipped to inclusive expiry."""
    start = add_period(anchor, period, index)
    if start > expiry:
        return None
    nominal_end = add_period(anchor, period, index + 1)
    end = min(nominal_end, expiry + timedelta(days=1))
    if start >= end:
        return None
    return BillingPeriod(start=start, end=end, nominal_end=nominal_end)


def period_index_for_date(anchor: date, period: str, target: date) -> int:
    """Find the latest anchor-derived boundary at or before target."""
    if target < anchor:
        return 0
    if period == Subscription.Period.DAILY:
        return (target - anchor).days
    if period == Subscription.Period.WEEKLY:
        return (target - anchor).days // 7
    if period == Subscription.Period.MONTHLY:
        estimate = (target.year - anchor.year) * 12 + target.month - anchor.month
    elif period == Subscription.Period.YEARLY:
        estimate = target.year - anchor.year
    else:
        raise ValueError(f"Unsupported billing period: {period}")
    while estimate and add_period(anchor, period, estimate) > target:
        estimate -= 1
    while add_period(anchor, period, estimate + 1) <= target:
        estimate += 1
    return estimate
