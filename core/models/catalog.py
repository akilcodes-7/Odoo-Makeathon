from django.db import models
from django.db.models import Q

from .base import TimestampedModel, user_reference


class Product(TimestampedModel):
    class Type(models.TextChoices):
        SOFTWARE = "SOFTWARE", "Software"
        SERVICE = "SERVICE", "Service"
        ADDON = "ADDON", "Add-on"

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=Type.choices)
    sales_price_paise = models.BigIntegerField()
    cost_price_paise = models.BigIntegerField()
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = user_reference(null=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(sales_price_paise__gte=0), name="product_sales_nonneg"),
            models.CheckConstraint(condition=Q(cost_price_paise__gte=0), name="product_cost_price_nonnegative"),
        ]

    def __str__(self):
        return self.name


class ProductVariant(TimestampedModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="variants")
    attribute_name = models.CharField(max_length=100)
    attribute_value = models.CharField(max_length=150)
    extra_price_paise = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = user_reference(null=True)

    class Meta:
        ordering = ["product__name", "attribute_name", "attribute_value", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "attribute_name", "attribute_value"],
                name="variant_attribute_value_uniq",
            ),
        ]
        indexes = [models.Index(fields=["product", "is_active"], name="variant_product_active_idx")]

    def __str__(self):
        return f"{self.product}: {self.attribute_name} {self.attribute_value}"


class Tax(TimestampedModel):
    name = models.CharField(max_length=120)
    rate_bps = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)
    created_by = user_reference(null=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(rate_bps__gte=0) & Q(rate_bps__lte=10000), name="tax_rate_bps_0_10000"),
        ]

    def __str__(self):
        return f"{self.name} ({self.rate_bps} bps)"


class Plan(TimestampedModel):
    class Period(models.TextChoices):
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"

    name = models.CharField(max_length=200)
    primary_product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="plans")
    price_paise = models.BigIntegerField()
    period = models.CharField(max_length=10, choices=Period.choices)
    min_quantity = models.PositiveIntegerField(default=1)
    available_from = models.DateField()
    available_until = models.DateField(null=True, blank=True)
    auto_close = models.BooleanField(default=False)
    closable = models.BooleanField(default=True)
    pausable = models.BooleanField(default=False)
    renewable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_by = user_reference(null=True)

    class Meta:
        ordering = ["name", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(price_paise__gte=0), name="plan_price_nonnegative"),
            models.CheckConstraint(condition=Q(min_quantity__gte=1), name="plan_min_quantity_positive"),
            models.CheckConstraint(
                condition=Q(available_until__isnull=True) | Q(available_until__gte=models.F("available_from")),
                name="plan_available_dates_ordered",
            ),
        ]
        indexes = [models.Index(fields=["is_active", "available_from"], name="plan_active_from_idx")]

    def __str__(self):
        return f"{self.name} ({self.get_period_display()})"
