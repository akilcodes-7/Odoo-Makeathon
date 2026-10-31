import uuid

from django.db import models
from django.db.models import Q

from .base import user_reference


class Payment(models.Model):
    class Method(models.TextChoices):
        BANK = "BANK", "Bank transfer"
        CARD = "CARD", "Card"
        CASH = "CASH", "Cash"
        OTHER = "OTHER", "Other"

    invoice = models.ForeignKey("Invoice", on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=5, choices=Method.choices)
    amount_paise = models.BigIntegerField()
    paid_on = models.DateField()
    note = models.TextField(blank=True)
    created_by = user_reference()
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_on", "-pk"]
        indexes = [
            models.Index(fields=["invoice", "paid_on"], name="payment_invoice_paid_idx"),
            models.Index(fields=["paid_on"], name="payment_paid_date_idx"),
        ]
        constraints = [models.CheckConstraint(condition=Q(amount_paise__gt=0), name="payment_amount_positive")]

    def __str__(self):
        return f"Payment {self.pk} for {self.invoice}"
