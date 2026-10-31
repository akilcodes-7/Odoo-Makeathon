"""Shared invoice balance selector used by lifecycle and finance workflows."""

from django.db.models import Sum

from core.models import Invoice, Payment


def get_invoice_balance(invoice_id: int) -> int:
    """Return the persisted outstanding amount in integer paise."""
    invoice = Invoice.objects.only("pk", "total_paise").get(pk=invoice_id)
    paid = Payment.objects.filter(invoice_id=invoice.pk).aggregate(total=Sum("amount_paise"))["total"] or 0
    return invoice.total_paise - paid
