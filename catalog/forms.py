from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import forms

from core.models import Plan, Product, ProductVariant, Tax


class RupeeField(forms.CharField):
    """Accept rupees as a decimal string and store an exact integer paise."""

    default_error_messages = {"invalid": "Enter a valid amount with at most two decimal places.", "negative": "Amount cannot be negative."}

    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return None
        try:
            amount = Decimal(value.strip().replace(",", ""))
            if not amount.is_finite() or amount.as_tuple().exponent < -2:
                raise InvalidOperation
            if amount < 0 and not getattr(self, "allow_negative", False):
                raise forms.ValidationError(self.error_messages["negative"], code="negative")
            return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except (InvalidOperation, ValueError):
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")

    def prepare_value(self, value):
        if value is None or value == "":
            return ""
        if isinstance(value, int):
            return f"{Decimal(value) / 100:.2f}"
        # Bound redisplay: value is already the user's submitted string; return as-is.
        return str(value)


class PercentField(forms.CharField):
    default_error_messages = {"invalid": "Enter a percentage from 0 to 100 with at most two decimal places."}

    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return None
        try:
            amount = Decimal(value.strip())
            if not amount.is_finite() or amount < 0 or amount > 100 or amount.as_tuple().exponent < -2:
                raise InvalidOperation
            return int(amount * 100)
        except (InvalidOperation, ValueError):
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")

    def prepare_value(self, value):
        if value is None or value == "":
            return ""
        if isinstance(value, int):
            return f"{Decimal(value) / 100:.2f}"
        # Bound redisplay: value is already the user's submitted string; return as-is.
        return str(value)


class PaiseModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.paise_fields:
            self.fields[name] = RupeeField(label=self.fields[name].label, help_text="Enter rupees; saved to exact paise.", initial=getattr(self.instance, name, None), required=self.fields[name].required)

    def _post_clean(self):
        # ModelForms expect model values during model validation; retain paise integers.
        for name in self.paise_fields:
            if name in self.cleaned_data:
                setattr(self.instance, name, self.cleaned_data[name])
        super()._post_clean()


class ProductForm(PaiseModelForm):
    paise_fields = ("sales_price_paise", "cost_price_paise")
    class Meta:
        model = Product
        fields = ("name", "type", "sales_price_paise", "cost_price_paise", "notes")
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class VariantForm(PaiseModelForm):
    paise_fields = ("extra_price_paise",)
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True), help_text="Choose the product this variant belongs to.")
    class Meta:
        model = ProductVariant
        fields = ("product", "attribute_name", "attribute_value", "extra_price_paise")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["extra_price_paise"].allow_negative = True

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        surcharge = cleaned.get("extra_price_paise")
        if product and surcharge is not None and product.sales_price_paise + surcharge < 0:
            self.add_error("extra_price_paise", "The resulting product price cannot be negative.")
        if product and surcharge is not None and product.plans.filter(is_active=True, price_paise__lt=-surcharge).exists():
            self.add_error("extra_price_paise", "This surcharge would make an active plan price negative.")
        return cleaned


class PlanForm(PaiseModelForm):
    paise_fields = ("price_paise",)
    primary_product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True), help_text="The plan price is the recurring unit price of this product.")
    class Meta:
        model = Plan
        fields = ("name", "primary_product", "price_paise", "period", "min_quantity", "available_from", "available_until", "auto_close", "closable", "pausable", "renewable")
        widgets = {"available_from": forms.DateInput(attrs={"type": "date"}), "available_until": forms.DateInput(attrs={"type": "date"})}

    def clean_min_quantity(self):
        quantity = self.cleaned_data["min_quantity"]
        if quantity < 1:
            raise forms.ValidationError("Minimum quantity must be at least one.")
        return quantity

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("available_from"), cleaned.get("available_until")
        if start and end and end < start:
            self.add_error("available_until", "Availability end must be on or after the start date.")
        price = cleaned.get("price_paise")
        product = cleaned.get("primary_product")
        if price is not None and product and product.variants.filter(is_active=True, extra_price_paise__lt=-price).exists():
            self.add_error("price_paise", "The selected product has an active variant that would make this plan price negative.")
        return cleaned


class TaxForm(forms.ModelForm):
    rate_percent = PercentField(label="Rate (%)", help_text="Enter 0–100 with up to two decimal places.")
    class Meta:
        model = Tax
        fields = ("name",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rate_percent"].initial = None if self.instance._state.adding else self.instance.rate_bps

    def clean_rate_percent(self):
        return self.cleaned_data["rate_percent"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.rate_bps = self.cleaned_data["rate_percent"]
        if commit:
            instance.save()
        return instance
