from django import forms
from django.db import IntegrityError, transaction

from core.models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("display_name", "billing_email", "phone", "billing_address", "is_active")
        widgets = {"display_name": forms.TextInput(attrs={"class": "form-control"}),
                   "billing_email": forms.EmailInput(attrs={"class": "form-control"}),
                   "phone": forms.TextInput(attrs={"class": "form-control"}),
                   "billing_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                   "is_active": forms.CheckboxInput()}


class OwnCustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("display_name", "billing_email", "phone", "billing_address")
        widgets = {"display_name": forms.TextInput(attrs={"class": "form-control"}),
                   "billing_email": forms.EmailInput(attrs={"class": "form-control"}),
                   "phone": forms.TextInput(attrs={"class": "form-control"}),
                   "billing_address": forms.Textarea(attrs={"class": "form-control", "rows": 3})}


def create_customer(form):
    """Create an internal customer without implicitly linking an account."""
    try:
        with transaction.atomic():
            customer = form.save(commit=False)
            customer.user = None
            customer.save()
            return customer
    except IntegrityError as exc:
        raise forms.ValidationError("This customer could not be saved.") from exc
