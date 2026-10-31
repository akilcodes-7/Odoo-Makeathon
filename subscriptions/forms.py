from datetime import timedelta
from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from accounts.models import User
from core.models import Customer, Plan, Product, ProductVariant, QuoteTemplate, Subscription, SubscriptionLine, Tax
from core.services.money import decimal_to_paise


class DraftSubscriptionForm(forms.ModelForm):
    quote_template = forms.ModelChoiceField(
        queryset=QuoteTemplate.objects.none(), required=False,
        label="Quotation template (optional)",
        help_text="A selected template copies its lines and prices into this draft.",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Subscription
        fields = ("customer", "plan", "quote_template", "start_date", "expiry_date", "quote_expires_on", "payment_terms_days")
        widgets = {
            "customer": forms.Select(attrs={"class": "form-control"}),
            "plan": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "quote_expires_on": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "payment_terms_days": forms.NumberInput(attrs={"min": 0, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.filter(is_active=True).order_by("display_name")
        self.fields["plan"].queryset = Plan.objects.filter(is_active=True, primary_product__is_active=True).order_by("name")
        self.fields["quote_template"].queryset = QuoteTemplate.objects.filter(
            is_active=True, plan__is_active=True, plan__primary_product__is_active=True,
        ).select_related("plan").order_by("name")
        if not self.instance.pk:
            self.initial.setdefault("quote_expires_on", timezone.localdate() + timedelta(days=7))

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        expiry = cleaned.get("expiry_date")
        plan = cleaned.get("plan")
        if start and expiry and expiry < start:
            self.add_error("expiry_date", "Expiry date must be on or after the start date.")
        if start and plan:
            if start < plan.available_from or (plan.available_until and start > plan.available_until):
                self.add_error("start_date", "The plan is not available on that start date.")
        quote_expiry = cleaned.get("quote_expires_on")
        if quote_expiry and quote_expiry < timezone.localdate():
            self.add_error("quote_expires_on", "Quotation expiry cannot be in the past.")
        template = cleaned.get("quote_template")
        if template and plan and template.plan_id != plan.pk:
            self.add_error("quote_template", "Choose a template for the selected plan.")
        return cleaned


class SubscriptionLineForm(forms.ModelForm):
    unit_price = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, label="Unit price (₹)", widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}))

    class Meta:
        model = SubscriptionLine
        fields = ("product", "variant", "is_primary", "quantity", "taxes", "position")
        widgets = {
            "product": forms.Select(attrs={"class": "form-control"}),
            "variant": forms.Select(attrs={"class": "form-control"}),
            "is_primary": forms.CheckboxInput(),
            "quantity": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "taxes": forms.SelectMultiple(attrs={"class": "form-control", "size": 4}),
            "position": forms.HiddenInput(),
        }

    def __init__(self, *args, plan=None, **kwargs):
        self.plan = plan
        super().__init__(*args, **kwargs)
        self.fields["product"].required = False
        self.fields["quantity"].required = False
        self.fields["position"].required = False
        self.fields["product"].queryset = Product.objects.filter(is_active=True).order_by("name")
        self.fields["variant"].queryset = ProductVariant.objects.filter(is_active=True, product__is_active=True).select_related("product")
        self.fields["taxes"].queryset = Tax.objects.filter(is_active=True).order_by("name")
        if self.instance and self.instance.pk and not self.is_bound:
            self.initial["unit_price"] = Decimal(self.instance.unit_price_paise) / Decimal(100)

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        variant = cleaned.get("variant")
        quantity = cleaned.get("quantity")
        price = cleaned.get("unit_price")
        if not product and price is None and not cleaned.get("is_primary"):
            return cleaned
        if variant and product and variant.product_id != product.pk:
            self.add_error("variant", "Choose a variant belonging to the selected product.")
        if cleaned.get("is_primary") and self.plan and product and product.pk != self.plan.primary_product_id:
            self.add_error("product", "The primary line must match the selected plan's product.")
        if cleaned.get("is_primary") and self.plan and quantity and quantity < self.plan.min_quantity:
            self.add_error("quantity", f"The primary line needs at least {self.plan.min_quantity} units.")
        if price is None and product:
            base_paise = (
                self.plan.price_paise if cleaned.get("is_primary") and self.plan
                else product.sales_price_paise
            )
            if cleaned.get("is_primary") and self.plan and product.pk != self.plan.primary_product_id:
                base_paise = product.sales_price_paise
            if variant and variant.product_id == product.pk:
                base_paise += variant.extra_price_paise
            try:
                price = Decimal(base_paise) / Decimal(100)
                cleaned["unit_price"] = price
            except Exception:
                self.add_error("unit_price", "Enter a valid line price.")
        if price is not None and price < 0:
            self.add_error("unit_price", "Price cannot be negative.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.unit_price_paise = decimal_to_paise(str(self.cleaned_data["unit_price"]))
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class BaseSubscriptionLineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.plan = kwargs.pop("plan", None)
        if not args or args[0] is None:
            if self.plan and not kwargs.get("initial"):
                kwargs["initial"] = [{
                    "product": self.plan.primary_product_id,
                    "is_primary": True,
                    "quantity": self.plan.min_quantity,
                    "position": 0,
                    "unit_price": Decimal(self.plan.price_paise) / Decimal(100),
                }]
        super().__init__(*args, **kwargs)
        for form in self.forms:
            form.plan = self.plan

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        rows = [
            form.cleaned_data for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False)
            and (form.cleaned_data.get("product") or form.cleaned_data.get("unit_price") is not None)
        ]
        primary = [row for row in rows if row.get("is_primary")]
        if len(primary) != 1:
            raise forms.ValidationError("Add exactly one primary product line.")
        if self.plan and primary[0].get("product") != self.plan.primary_product:
            raise forms.ValidationError("The primary line must match the selected plan.")

    def save_new_objects(self, commit=True):
        self.new_objects = []
        saved = []
        for form in self.extra_forms:
            if not form.has_changed() or self._should_delete_form(form):
                continue
            cleaned = getattr(form, "cleaned_data", {})
            if not cleaned.get("product") and cleaned.get("unit_price") is None and not cleaned.get("is_primary"):
                continue
            self.new_objects.append(self.save_new(form, commit=commit))
            saved.append(self.new_objects[-1])
        return saved


SubscriptionLineFormSet = inlineformset_factory(
    Subscription, SubscriptionLine, form=SubscriptionLineForm,
    formset=BaseSubscriptionLineFormSet, extra=2, can_delete=True,
)
