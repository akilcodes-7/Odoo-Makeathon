"""Restricted Django admin for internal setup and read-only audit views.

Financial status and payment changes stay in domain services. Subscription,
invoice, payment, redemption and event rows are visible for support but cannot
be edited, added or deleted from Django admin.
"""

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import (
    Customer,
    Discount,
    DiscountRedemption,
    Invoice,
    InvoiceLine,
    InvoiceLineTax,
    Payment,
    Plan,
    Product,
    ProductVariant,
    QuoteTemplate,
    QuoteTemplateLine,
    Subscription,
    SubscriptionEvent,
    SubscriptionLine,
    Tax,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Provide an internal audit view without a mutation back door."""

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields) + tuple(
            field.name for field in self.model._meta.many_to_many
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ("attribute_name", "attribute_value", "extra_price_paise", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "sales_price_paise", "cost_price_paise", "is_active")
    list_filter = ("type", "is_active")
    search_fields = ("name", "notes")
    inlines = (ProductVariantInline,)
    readonly_fields = ("created_at", "updated_at", "created_by")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "period", "price_paise", "min_quantity", "is_active")
    list_filter = ("period", "auto_close", "closable", "pausable", "renewable", "is_active")
    search_fields = ("name", "primary_product__name")
    readonly_fields = ("created_at", "updated_at", "created_by")


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ("name", "rate_bps", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at", "created_by")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "billing_email", "user", "is_active")
    list_filter = ("is_active",)
    search_fields = ("display_name", "billing_email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "scope", "used_count", "max_uses", "is_active")
    list_filter = ("kind", "scope", "is_active")
    search_fields = ("name",)
    readonly_fields = ("used_count", "created_at", "updated_at", "created_by")


class QuoteTemplateLineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        rows = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
        ]
        primary_rows = [row for row in rows if row.get("is_primary")]
        if len(primary_rows) != 1:
            raise ValidationError("A quotation template needs exactly one primary product line.")

        primary = primary_rows[0]
        plan = self.instance.plan
        if primary.get("product") != plan.primary_product:
            raise ValidationError("The primary quotation line must match the plan's product.")
        if primary.get("quantity", 0) < plan.min_quantity:
            raise ValidationError("The primary quotation quantity is below the plan minimum.")


class QuoteTemplateLineInline(admin.TabularInline):
    model = QuoteTemplateLine
    extra = 0
    fields = ("product", "variant", "is_primary", "quantity", "unit_price_paise", "taxes", "position")
    formset = QuoteTemplateLineFormSet


@admin.register(QuoteTemplate)
class QuoteTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "validity_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "plan__name")
    inlines = (QuoteTemplateLineInline,)
    readonly_fields = ("created_at", "updated_at", "created_by")


@admin.register(Subscription)
class SubscriptionAdmin(ReadOnlyAdmin):
    list_display = ("number", "customer", "plan", "status", "start_date", "expiry_date")
    list_filter = ("status", "billing_period", "is_paused")
    search_fields = ("number", "customer__display_name", "customer__billing_email")
    date_hierarchy = "start_date"


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    fields = (
        "product_name", "variant_description", "quantity", "unit_price_paise",
        "subtotal_paise", "discount_paise", "taxable_paise", "tax_paise", "total_paise",
    )
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(ReadOnlyAdmin):
    list_display = ("number", "subscription", "status", "invoice_date", "due_date", "total_paise")
    list_filter = ("status", "invoice_date")
    search_fields = ("number", "customer_name", "customer_email", "subscription__number")
    date_hierarchy = "invoice_date"
    inlines = (InvoiceLineInline,)


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ("invoice", "method", "amount_paise", "paid_on", "created_by")
    list_filter = ("method", "paid_on")
    search_fields = ("invoice__number", "note")
    date_hierarchy = "paid_on"


@admin.register(DiscountRedemption)
class DiscountRedemptionAdmin(ReadOnlyAdmin):
    list_display = ("invoice", "discount_name", "total_discount_paise")
    search_fields = ("invoice__number", "discount_name")


@admin.register(InvoiceLineTax)
class InvoiceLineTaxAdmin(ReadOnlyAdmin):
    list_display = ("invoice_line", "tax_name", "rate_bps", "amount_paise")
    search_fields = ("invoice_line__invoice__number", "tax_name")


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(ReadOnlyAdmin):
    list_display = ("subscription", "action", "from_status", "to_status", "occurred_at", "actor")
    list_filter = ("action", "occurred_at")
    search_fields = ("subscription__number", "note")
    date_hierarchy = "occurred_at"
