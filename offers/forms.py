from decimal import Decimal, InvalidOperation

from django import forms

from core.models import Discount, Product


class RupeeField(forms.CharField):
    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return None
        try:
            amount = Decimal(value.strip().replace(",", ""))
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Enter a nonnegative rupee amount with at most two decimal places.")
        if not amount.is_finite() or amount < 0 or max(0, -amount.as_tuple().exponent) > 2:
            raise forms.ValidationError("Enter a nonnegative rupee amount with at most two decimal places.")
        return int(amount * 100)

    def prepare_value(self, value):
        if value in self.empty_values:
            return ""
        if isinstance(value, int):
            return f"{Decimal(value) / Decimal(100):.2f}"
        # Bound redisplay: value is already the user's submitted string; return as-is.
        return str(value)


class PercentField(forms.CharField):
    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return None
        try:
            amount = Decimal(value.strip())
        except (InvalidOperation, ValueError):
            raise forms.ValidationError("Enter a percentage from 0 to 100 with at most two decimal places.")
        if not amount.is_finite() or not 0 <= amount <= 100 or max(0, -amount.as_tuple().exponent) > 2:
            raise forms.ValidationError("Enter a percentage from 0 to 100 with at most two decimal places.")
        return int(amount * 100)

    def prepare_value(self, value):
        if value in self.empty_values:
            return ""
        if isinstance(value, int):
            return f"{Decimal(value) / Decimal(100):.2f}"
        # Bound redisplay: value is already the user's submitted string; return as-is.
        return str(value)


class DiscountForm(forms.ModelForm):
    amount_rupees = RupeeField(label="Fixed amount (₹)", required=False, help_text="Used for fixed rules; saved as integer paise.")
    percent = PercentField(label="Percentage (%)", required=False, help_text="Used for percentage rules; enter up to two decimal places.")
    products = forms.ModelMultipleChoiceField(queryset=Product.objects.order_by("name", "pk"), required=False, help_text="Required for selected-products scope.")

    class Meta:
        model = Discount
        fields = (
            "name", "kind", "scope", "min_purchase_paise", "min_quantity",
            "starts_on", "ends_on", "max_uses", "products", "is_active",
        )
        widgets = {
            "starts_on": forms.DateInput(attrs={"type": "date"}),
            "ends_on": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "min_purchase_paise": "Eligible pre-tax, pre-discount subtotal in rupees.",
            "min_quantity": "Eligible total quantity; zero disables this minimum.",
            "max_uses": "Leave blank for no cap. Existing use count cannot be reduced below its current value.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["min_purchase_paise"] = RupeeField(
            label="Minimum purchase (₹)", required=True,
            help_text=self.Meta.help_texts["min_purchase_paise"],
            initial=self.instance.min_purchase_paise if self.instance.pk else 0,
        )
        self.fields["amount_rupees"].initial = self.instance.amount_paise
        self.fields["percent"].initial = self.instance.percent_bps
        self.fields["products"].initial = self.instance.products.all() if self.instance.pk else None

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        if kind == Discount.Kind.FIXED:
            if cleaned.get("amount_rupees") is None:
                self.add_error("amount_rupees", "Enter the fixed discount amount.")
            if cleaned.get("percent") is not None:
                self.add_error("percent", "Leave percentage blank for a fixed rule.")
        elif kind == Discount.Kind.PERCENT:
            if cleaned.get("percent") is None:
                self.add_error("percent", "Enter the percentage discount.")
            if cleaned.get("amount_rupees") is not None:
                self.add_error("amount_rupees", "Leave fixed amount blank for a percentage rule.")
        if cleaned.get("scope") == Discount.Scope.PRODUCTS and not cleaned.get("products"):
            self.add_error("products", "Choose at least one product for selected-products scope.")
        starts, ends = cleaned.get("starts_on"), cleaned.get("ends_on")
        if starts and ends and ends < starts:
            self.add_error("ends_on", "End date must be on or after start date.")
        max_uses = cleaned.get("max_uses")
        if max_uses is not None and self.instance.pk and max_uses < self.instance.used_count:
            self.add_error("max_uses", "Maximum uses cannot be lower than the number already redeemed.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.min_purchase_paise = self.cleaned_data["min_purchase_paise"]
        if instance.kind == Discount.Kind.FIXED:
            instance.amount_paise = self.cleaned_data["amount_rupees"]
            instance.percent_bps = None
        else:
            instance.amount_paise = None
            instance.percent_bps = self.cleaned_data["percent"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance
