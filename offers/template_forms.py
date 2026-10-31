from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from core.models import Product, ProductVariant, QuoteTemplate, QuoteTemplateLine, Tax
from core.services.money import decimal_to_paise


class QuoteTemplateForm(forms.ModelForm):
    class Meta:
        model = QuoteTemplate
        fields = ("name", "plan", "validity_days", "notes", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "plan": forms.Select(attrs={"class": "form-control"}),
            "validity_days": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = self.fields["plan"].queryset.filter(is_active=True).select_related("primary_product")


class QuoteTemplateLineForm(forms.ModelForm):
    unit_price = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"),
        label="Unit price (₹)", widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
    )

    class Meta:
        model = QuoteTemplateLine
        fields = ("product", "variant", "is_primary", "quantity", "unit_price", "taxes", "position")
        widgets = {
            "product": forms.Select(attrs={"class": "form-control"}),
            "variant": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "taxes": forms.SelectMultiple(attrs={"class": "form-control", "size": 4}),
            "position": forms.NumberInput(attrs={"min": 0, "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True).order_by("name")
        self.fields["variant"].queryset = ProductVariant.objects.filter(is_active=True, product__is_active=True).select_related("product")
        self.fields["taxes"].queryset = Tax.objects.filter(is_active=True).order_by("name")
        if self.instance and self.instance.pk and not self.is_bound:
            self.initial["unit_price"] = Decimal(self.instance.unit_price_paise) / Decimal(100)

    def clean(self):
        cleaned = super().clean()
        product, variant = cleaned.get("product"), cleaned.get("variant")
        if product and variant and variant.product_id != product.pk:
            self.add_error("variant", "Choose a variant belonging to the selected product.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.unit_price_paise = decimal_to_paise(str(self.cleaned_data["unit_price"]))
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class BaseQuoteTemplateLineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        rows = [form.cleaned_data for form in self.forms if form.cleaned_data and not form.cleaned_data.get("DELETE")]
        primaries = [row for row in rows if row.get("is_primary")]
        if len(primaries) != 1:
            raise forms.ValidationError("Add exactly one primary product line.")
        if self.instance.plan_id and primaries[0].get("product") and primaries[0]["product"].pk != self.instance.plan.primary_product_id:
            raise forms.ValidationError("The primary line must match the selected plan.")
        if self.instance.plan_id and primaries[0].get("quantity", 0) < self.instance.plan.min_quantity:
            raise forms.ValidationError(f"The primary line needs at least {self.instance.plan.min_quantity} units.")


QuoteTemplateLineFormSet = inlineformset_factory(
    QuoteTemplate, QuoteTemplateLine, form=QuoteTemplateLineForm,
    formset=BaseQuoteTemplateLineFormSet, extra=1, can_delete=True,
)
