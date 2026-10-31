"""Stable billing hook for discount rules.

The empty implementation is intentional in the S0 spine. The billing engine
can calculate and snapshot a discount returned by this hook without importing
discount model details. The Offers owner replaces this hook in T1A.
"""

from typing import TYPE_CHECKING

from core.services.pricing import BillingPeriod, DiscountApplication, LineBase

if TYPE_CHECKING:
    from core.models import Subscription
    from core.models import Invoice


def get_applicable_discounts(
    subscription: "Subscription",
    period: BillingPeriod,
    *,
    line_bases: list[LineBase],
) -> list[DiscountApplication]:
    """Return eligible discount candidates for a subscription billing period.

    S0 returns no candidates. T1A implements eligibility and deterministic
    allocation while keeping this signature stable.
    """

    del subscription, period, line_bases
    return []


def reserve_discount_usage(
    application: DiscountApplication,
    invoice: "Invoice",
) -> None:
    """Reserve one use inside the caller's invoice transaction.

    There are no applications in S0, so reaching this stub signals a wiring
    error. T1A replaces it with a conditional, atomic counter increment.
    """

    del application, invoice
    return None

