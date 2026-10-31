from django.db import models
from django.db.models import Q

from .base import TimestampedModel, user_reference


class Discount(TimestampedModel):
    class Kind(models.TextChoices):
        FIXED = "FIXED", "Fixed amount"
        PERCENT = "PERCENT", "Percentage"

    class Scope(models.TextChoices):
        PRODUCTS = "PRODUCTS", "Selected products"
        SUBSCRIPTION = "SUBSCRIPTION", "Whole subscription"

    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    amount_paise = models.BigIntegerField(null=True, blank=True)
    percent_bps = models.PositiveSmallIntegerField(null=True, blank=True)
    scope = models.CharField(max_length=15, choices=Scope.choices)
    products = models.ManyToManyField("Product", blank=True, related_name="discounts")
    min_purchase_paise = models.BigIntegerField(default=0)
    min_quantity = models.PositiveIntegerField(default=0)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = user_reference(null=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(kind="FIXED", amount_paise__isnull=False, percent_bps__isnull=True)
                    | Q(kind="PERCENT", amount_paise__isnull=True, percent_bps__isnull=False)
                ),
                name="discount_value_matches_kind",
            ),
            models.CheckConstraint(
                condition=Q(amount_paise__isnull=True) | Q(amount_paise__gte=0),
                name="discount_amount_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(percent_bps__isnull=True) | Q(percent_bps__lte=10000),
                name="discount_percent_max_10000_bps",
            ),
            models.CheckConstraint(condition=Q(min_purchase_paise__gte=0), name="discount_min_purchase_nonneg"),
            models.CheckConstraint(condition=Q(used_count__gte=0), name="discount_used_count_nonneg"),
            models.CheckConstraint(condition=Q(max_uses__isnull=True) | Q(max_uses__gt=0), name="discount_max_uses_positive"),
            models.CheckConstraint(
                condition=Q(max_uses__isnull=True) | Q(used_count__lte=models.F("max_uses")),
                name="discount_capacity_not_exceeded",
            ),
            models.CheckConstraint(
                condition=Q(ends_on__isnull=True) | Q(ends_on__gte=models.F("starts_on")),
                name="discount_dates_ordered",
            ),
        ]
        indexes = [models.Index(fields=["is_active", "starts_on", "ends_on"], name="discount_active_dates_idx")]

    def __str__(self):
        return self.name


class DiscountRedemption(TimestampedModel):
    invoice = models.OneToOneField("Invoice", on_delete=models.PROTECT, related_name="discount_redemption")
    discount = models.ForeignKey(Discount, on_delete=models.PROTECT, related_name="redemptions")
    discount_name = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=Discount.Kind.choices)
    value_paise = models.BigIntegerField(null=True, blank=True)
    value_bps = models.PositiveSmallIntegerField(null=True, blank=True)
    total_discount_paise = models.BigIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(kind="FIXED", value_paise__isnull=False, value_bps__isnull=True)
                    | Q(kind="PERCENT", value_paise__isnull=True, value_bps__isnull=False)
                ),
                name="redemption_value_matches_kind",
            ),
            models.CheckConstraint(
                condition=Q(value_paise__isnull=True) | Q(value_paise__gte=0),
                name="redemption_value_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(value_bps__isnull=True) | Q(value_bps__lte=10000),
                name="redemption_percent_max",
            ),
            models.CheckConstraint(
                condition=Q(total_discount_paise__gte=0),
                name="redemption_total_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.discount_name} on {self.invoice}"
