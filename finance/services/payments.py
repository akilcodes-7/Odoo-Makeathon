"""Transactional payment recording and persisted invoice balance selectors."""

from datetime import date, datetime
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from core.models import Invoice, Payment
from core.services.exceptions import DomainValidationError


def get_invoice_balance(invoice_id: int) -> int:
    """Return outstanding invoice balance in integer paise."""
    from core.services.finance import get_invoice_balance as shared_balance

    return shared_balance(invoice_id)


def invoice_is_overdue(invoice_id: int, *, as_of=None) -> bool:
    """Apply the spec's overdue rule: confirmed, due before as_of, balance > 0."""
    invoice = Invoice.objects.only("pk", "status", "due_date").get(pk=invoice_id)
    as_of = as_of or timezone.localdate()
    return (
        invoice.status == Invoice.Status.CONFIRMED
        and invoice.due_date < as_of
        and get_invoice_balance(invoice.pk) > 0
    )


def _validated_payload(*, invoice_id, amount_paise, method, paid_on, note, idempotency_key):
    try:
        invoice_id = int(invoice_id)
        key = idempotency_key if isinstance(idempotency_key, UUID) else UUID(str(idempotency_key))
    except (TypeError, ValueError, AttributeError):
        raise DomainValidationError("invalid_payment", "Invoice and idempotency key must be valid.")
    if isinstance(amount_paise, bool) or not isinstance(amount_paise, int) or not 0 < amount_paise <= 9_223_372_036_854_775_807:
        raise DomainValidationError("invalid_amount", "Enter a positive payment amount in paise.", {"amount_paise": "Amount must be greater than zero."})
    if method not in Payment.Method.values:
        raise DomainValidationError("invalid_method", "Choose a valid payment method.", {"method": "Choose a valid method."})
    if isinstance(paid_on, str):
        try:
            paid_on = date.fromisoformat(paid_on)
        except ValueError:
            paid_on = None
    if not isinstance(paid_on, date) or isinstance(paid_on, datetime):
        raise DomainValidationError("invalid_paid_on", "Enter a valid payment date.", {"paid_on": "Enter a valid date."})
    if note is None:
        note = ""
    if not isinstance(note, str):
        raise DomainValidationError("invalid_note", "Payment note must be text.", {"note": "Enter text."})
    note = note.strip()
    if len(note) > 10000:
        raise DomainValidationError("invalid_note", "Payment note is too long.", {"note": "Use at most 10,000 characters."})
    return invoice_id, amount_paise, method, paid_on, note, key


def _same_payload(payment, *, invoice_id, amount_paise, method, paid_on, note):
    return (
        payment.invoice_id == invoice_id
        and payment.amount_paise == amount_paise
        and payment.method == method
        and payment.paid_on == paid_on
        and payment.note == note
    )


def _replay_or_conflict(key, *, invoice_id, amount_paise, method, paid_on, note):
    prior = Payment.objects.filter(idempotency_key=key).first()
    if prior is None:
        return None
    if not _same_payload(prior, invoice_id=invoice_id, amount_paise=amount_paise, method=method, paid_on=paid_on, note=note):
        raise DomainValidationError("idempotency_conflict", "This submission key was already used for different payment details.")
    return prior


def record_payment(invoice_id, *, amount_paise, method, paid_on, note="", idempotency_key, actor):
    """Record one immutable payment, rechecking balance under an invoice lock."""
    invoice_id, amount_paise, method, paid_on, note, key = _validated_payload(
        invoice_id=invoice_id, amount_paise=amount_paise, method=method,
        paid_on=paid_on, note=note, idempotency_key=idempotency_key,
    )
    if paid_on > timezone.localdate():
        raise DomainValidationError("future_payment_date", "Payment date cannot be in the future.", {"paid_on": "Choose today or an earlier date."})
    try:
        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
            replay = _replay_or_conflict(key, invoice_id=invoice_id, amount_paise=amount_paise, method=method, paid_on=paid_on, note=note)
            if replay:
                return replay
            if invoice.status != Invoice.Status.CONFIRMED:
                raise DomainValidationError("invoice_not_payable", "Only confirmed invoices can receive payments.")
            paid = Payment.objects.filter(invoice_id=invoice_id).aggregate(total=Sum("amount_paise"))["total"] or 0
            balance = invoice.total_paise - paid
            if amount_paise > balance:
                raise DomainValidationError("payment_exceeds_balance", "Payment cannot exceed the current outstanding balance.", {"amount_paise": "Amount exceeds the remaining balance."})
            payment = Payment.objects.create(
                invoice=invoice, method=method, amount_paise=amount_paise, paid_on=paid_on,
                note=note, idempotency_key=key, created_by=actor,
            )
            if amount_paise == balance:
                from core.services.lifecycle import transition_invoice

                transition_invoice(invoice.pk, Invoice.Status.PAID, actor=actor)
            return payment
    except IntegrityError:
        # Covers a concurrent submission reusing the same UUID. The failed
        # transaction is over before looking up its winner.
        replay = _replay_or_conflict(key, invoice_id=invoice_id, amount_paise=amount_paise, method=method, paid_on=paid_on, note=note)
        if replay:
            return replay
        raise
