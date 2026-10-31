"""Exact INR parsing, rounding, and display helpers."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


PAISE = Decimal("100")
WHOLE = Decimal("1")


def decimal_to_paise(value: str | Decimal) -> int:
    """Parse rupees exactly, accepting at most two fractional digits."""
    if isinstance(value, float):
        raise TypeError("Money must not be converted from a binary float.")
    try:
        rupees = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Enter a valid amount.") from exc
    if not rupees.is_finite() or rupees < 0:
        raise ValueError("Amount must be a finite nonnegative value.")
    if max(0, -rupees.as_tuple().exponent) > 2:
        raise ValueError("Amount may have at most two decimal places.")
    return int((rupees * PAISE).quantize(WHOLE, rounding=ROUND_HALF_UP))


def round_half_up(value: Decimal) -> int:
    return int(value.quantize(WHOLE, rounding=ROUND_HALF_UP))


def prorate_paise(amount_paise: int, numerator_days: int, denominator_days: int) -> int:
    if amount_paise < 0 or numerator_days < 0 or denominator_days <= 0:
        raise ValueError("Invalid amount or proration days.")
    return round_half_up(Decimal(amount_paise) * Decimal(numerator_days) / Decimal(denominator_days))


def tax_paise(taxable_paise: int, rate_bps: int) -> int:
    if taxable_paise < 0 or not 0 <= rate_bps <= 10_000:
        raise ValueError("Invalid taxable amount or tax rate.")
    return round_half_up(Decimal(taxable_paise) * Decimal(rate_bps) / Decimal(10_000))


def format_paise(amount_paise: int) -> str:
    sign = "-" if amount_paise < 0 else ""
    rupees, paise = divmod(abs(amount_paise), 100)
    return f"{sign}₹{rupees:,}.{paise:02d}"
