from django.db import models
from django.db.models import Q

from .base import TimestampedModel, user_reference


class Invoice(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    number = models.CharField(max_length=32, unique=True)
    subscription = models.ForeignKey("Subscription", on_delete=models.PROTECT, related_name="invoices")
    period_start = models.DateField()
    period_end = models.DateField()
    invoice_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_address = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default="INR", editable=False)
    subtotal_paise = models.BigIntegerField(default=0)
    discount_paise = models.BigIntegerField(default=0)
    tax_paise = models.BigIntegerField(default=0)
    total_paise = models.BigIntegerField(default=0)
    terms_days_snapshot = models.PositiveIntegerField(default=0)
    created_by = user_reference(null=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-invoice_date", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["subscription", "period_start"], name="invoice_sub_period_uniq"),
            models.CheckConstraint(condition=Q(period_end__gt=models.F("period_start")), name="invoice_positive_period"),
            models.CheckConstraint(condition=Q(subtotal_paise__gte=0), name="invoice_subtotal_nonnegative"),
            models.CheckConstraint(condition=Q(discount_paise__gte=0), name="invoice_discount_nonnegative"),
            models.CheckConstraint(condition=Q(tax_paise__gte=0), name="invoice_tax_nonnegative"),
            models.CheckConstraint(condition=Q(total_paise__gte=0), name="invoice_total_nonnegative"),
            models.CheckConstraint(condition=Q(discount_paise__lte=models.F("subtotal_paise")), name="invoice_discount_capped"),
            models.CheckConstraint(
                condition=Q(total_paise=models.F("subtotal_paise") - models.F("discount_paise") + models.F("tax_paise")),
                name="invoice_total_reconciles",
            ),
            models.CheckConstraint(condition=Q(due_date__gte=models.F("invoice_date")), name="invoice_dates_ordered"),
            models.CheckConstraint(condition=Q(terms_days_snapshot__gte=0), name="invoice_terms_nonnegative"),
        ]
        indexes = [
            models.Index(fields=["status", "due_date"], name="invoice_status_due_idx"),
            models.Index(fields=["invoice_date"], name="invoice_date_idx"),
        ]

    def __str__(self):
        return self.number


class InvoiceLine(TimestampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    source_line = models.ForeignKey("SubscriptionLine", on_delete=models.PROTECT, related_name="invoice_lines")
    product_name = models.CharField(max_length=200)
    variant_description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price_paise = models.BigIntegerField()
    period_numerator_days = models.PositiveIntegerField()
    period_denominator_days = models.PositiveIntegerField()
    subtotal_paise = models.BigIntegerField()
    discount_paise = models.BigIntegerField(default=0)
    taxable_paise = models.BigIntegerField()
    tax_paise = models.BigIntegerField(default=0)
    total_paise = models.BigIntegerField()
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="invoice_line_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price_paise__gte=0), name="invoice_line_price_nonnegative"),
            models.CheckConstraint(condition=Q(period_numerator_days__gte=1), name="inv_line_num_days_positive"),
            models.CheckConstraint(condition=Q(period_denominator_days__gte=1), name="inv_line_den_days_positive"),
            models.CheckConstraint(condition=Q(subtotal_paise__gte=0), name="inv_line_subtotal_nonneg"),
            models.CheckConstraint(condition=Q(discount_paise__gte=0), name="inv_line_discount_nonneg"),
            models.CheckConstraint(condition=Q(taxable_paise__gte=0), name="inv_line_taxable_nonneg"),
            models.CheckConstraint(condition=Q(tax_paise__gte=0), name="invoice_line_tax_nonnegative"),
            models.CheckConstraint(condition=Q(total_paise__gte=0), name="invoice_line_total_nonnegative"),
            models.CheckConstraint(condition=Q(discount_paise__lte=models.F("subtotal_paise")), name="inv_line_discount_capped"),
            models.CheckConstraint(
                condition=Q(taxable_paise=models.F("subtotal_paise") - models.F("discount_paise")),
                name="inv_line_taxable_reconciles",
            ),
            models.CheckConstraint(
                condition=Q(total_paise=models.F("taxable_paise") + models.F("tax_paise")),
                name="inv_line_total_reconciles",
            ),
        ]


class InvoiceLineTax(models.Model):
    invoice_line = models.ForeignKey(InvoiceLine, on_delete=models.CASCADE, related_name="tax_snapshots")
    source_tax = models.ForeignKey("Tax", on_delete=models.PROTECT, related_name="invoice_tax_snapshots")
    tax_name = models.CharField(max_length=120)
    rate_bps = models.PositiveSmallIntegerField()
    amount_paise = models.BigIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(rate_bps__lte=10000), name="invoice_tax_snapshot_rate_max"),
            models.CheckConstraint(condition=Q(amount_paise__gte=0), name="invoice_tax_amount_nonneg"),
            models.UniqueConstraint(fields=["invoice_line", "source_tax"], name="invoice_line_tax_once"),
        ]
