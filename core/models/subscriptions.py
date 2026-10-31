from django.conf import settings
from django.db import models
from django.db.models import Q

from .base import TimestampedModel, user_reference


class QuoteTemplate(TimestampedModel):
    name = models.CharField(max_length=200)
    plan = models.ForeignKey("Plan", on_delete=models.PROTECT, related_name="quote_templates")
    validity_days = models.PositiveIntegerField(default=7)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = user_reference(null=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [models.CheckConstraint(condition=Q(validity_days__gte=1), name="quote_validity_positive")]

    def __str__(self):
        return self.name


class QuoteTemplateLine(TimestampedModel):
    template = models.ForeignKey(QuoteTemplate, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("Product", on_delete=models.PROTECT, related_name="quote_template_lines")
    variant = models.ForeignKey("ProductVariant", on_delete=models.PROTECT, null=True, blank=True, related_name="quote_template_lines")
    is_primary = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_paise = models.BigIntegerField()
    taxes = models.ManyToManyField("Tax", blank=True, related_name="quote_template_lines")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="quote_line_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price_paise__gte=0), name="quote_line_price_nonneg"),
            models.UniqueConstraint(
                fields=["template"], condition=Q(is_primary=True), name="quote_primary_line_uniq",
            ),
        ]


class Subscription(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        QUOTATION = "QUOTATION", "Quotation"
        CONFIRMED = "CONFIRMED", "Confirmed"
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    class Period(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"

    number = models.CharField(max_length=32, unique=True)
    customer = models.ForeignKey("Customer", on_delete=models.PROTECT, related_name="subscriptions")
    plan = models.ForeignKey("Plan", on_delete=models.PROTECT, related_name="subscriptions")
    renewed_from = models.OneToOneField("self", on_delete=models.PROTECT, null=True, blank=True, related_name="successor")
    source_template = models.ForeignKey(QuoteTemplate, on_delete=models.PROTECT, null=True, blank=True, related_name="subscriptions")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField()
    expiry_date = models.DateField()
    payment_terms_days = models.PositiveIntegerField(default=0)
    quote_expires_on = models.DateField(null=True, blank=True)
    billing_anchor_date = models.DateField()
    billing_period_index = models.PositiveIntegerField(default=0)
    next_invoice_date = models.DateField(null=True, blank=True)
    billing_period = models.CharField(max_length=10, choices=Period.choices)
    auto_close_snapshot = models.BooleanField(default=False)
    closable_snapshot = models.BooleanField(default=True)
    pausable_snapshot = models.BooleanField(default=False)
    renewable_snapshot = models.BooleanField(default=True)
    min_quantity_snapshot = models.PositiveIntegerField(default=1)
    is_paused = models.BooleanField(default=False)
    pause_effective_on = models.DateField(null=True, blank=True)
    closed_on = models.DateField(null=True, blank=True)
    closure_reason = models.TextField(blank=True)
    currency = models.CharField(max_length=3, default="INR", editable=False)
    created_by = user_reference(null=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=Q(expiry_date__gte=models.F("start_date")), name="subscription_expiry_ordered"),
            models.CheckConstraint(condition=Q(payment_terms_days__gte=0), name="subscription_terms_nonnegative"),
            models.CheckConstraint(condition=Q(billing_period_index__gte=0), name="sub_period_index_nonneg"),
            models.CheckConstraint(condition=Q(min_quantity_snapshot__gte=1), name="subscription_min_qty_positive"),
        ]
        indexes = [
            models.Index(fields=["status", "next_invoice_date"], name="subscription_due_idx"),
            models.Index(fields=["customer", "status"], name="sub_customer_status_idx"),
            models.Index(fields=["expiry_date"], name="subscription_expiry_idx"),
        ]

    def __str__(self):
        return self.number


class SubscriptionLine(TimestampedModel):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("Product", on_delete=models.PROTECT, related_name="subscription_lines")
    variant = models.ForeignKey("ProductVariant", on_delete=models.PROTECT, null=True, blank=True, related_name="subscription_lines")
    is_primary = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_paise = models.BigIntegerField()
    taxes = models.ManyToManyField("Tax", blank=True, related_name="subscription_lines")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="sub_line_qty_positive"),
            models.CheckConstraint(condition=Q(unit_price_paise__gte=0), name="sub_line_price_nonneg"),
            models.UniqueConstraint(
                fields=["subscription"], condition=Q(is_primary=True), name="subscription_one_primary_line",
            ),
        ]


class SubscriptionEvent(models.Model):
    class Action(models.TextChoices):
        STATUS = "STATUS", "Status transition"
        PAUSE = "PAUSE", "Pause"
        RESUME = "RESUME", "Resume"
        CLOSE = "CLOSE", "Close"
        RENEW = "RENEW", "Renew"

    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="subscription_events")
    action = models.CharField(max_length=10, choices=Action.choices)
    from_status = models.CharField(max_length=12, choices=Subscription.Status.choices, blank=True)
    to_status = models.CharField(max_length=12, choices=Subscription.Status.choices, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-occurred_at", "-pk"]
        indexes = [models.Index(fields=["subscription", "occurred_at"], name="subscription_event_time_idx")]
