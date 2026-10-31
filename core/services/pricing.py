"""Shared, immutable value objects for tax and subscription billing.

Amounts are integer paise. Rates are integer basis points (10000 == 100%).
Use ``Decimal`` for any ratios or rounding in the eventual calculators; never
convert an amount through a binary float.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class BillingPeriod:
    """A billable half-open service interval ``[start, end)``."""

    start: date
    end: date
    nominal_end: date

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError("A billing period must contain at least one day.")
        if self.start >= self.nominal_end:
            raise ValueError("A nominal billing period must contain at least one day.")
        if self.end > self.nominal_end:
            raise ValueError("The clipped billing end cannot exceed the nominal end.")

    @property
    def actual_days(self) -> int:
        return (self.end - self.start).days

    @property
    def nominal_days(self) -> int:
        return (self.nominal_end - self.start).days


@dataclass(frozen=True, slots=True)
class TaxSnapshot:
    """Tax identity and rate copied onto an invoice line at billing time."""

    tax_id: int
    name: str
    rate_bps: int


@dataclass(frozen=True, slots=True)
class LineBase:
    """A confirmed subscription line prepared for one billing period."""

    source_line_id: int
    product_id: int
    quantity: int
    unit_price_paise: int
    subtotal_paise: int
    taxes: tuple[TaxSnapshot, ...]


@dataclass(frozen=True, slots=True)
class DiscountApplication:
    """One deterministic discount, allocated by source line in integer paise."""

    discount_id: int
    name: str
    kind: str
    value_paise: int | None
    value_bps: int | None
    line_discounts: tuple[tuple[int, int], ...]
    total_discount_paise: int


@dataclass(frozen=True, slots=True)
class BillingResult:
    """Summary for one bounded billing invocation."""

    created_ids: tuple[int, ...] = ()
    existing_ids: tuple[int, ...] = ()
    errors: tuple[str, ...] = ()
    remaining_due_count: int = 0

