import uuid

from django import forms

from core.models import Payment
from core.services.money import decimal_to_paise


class PaymentForm(forms.Form):
    amount = forms.DecimalField(
        label="Amount (₹)", max_digits=12, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}),
    )
    method = forms.ChoiceField(label="Method", choices=Payment.Method.choices)
    paid_on = forms.DateField(label="Paid on", widget=forms.DateInput(attrs={"type": "date"}))
    note = forms.CharField(label="Note", required=False, max_length=10000, widget=forms.Textarea(attrs={"rows": 3}))
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)

    def clean_amount(self):
        value = self.cleaned_data["amount"]
        try:
            return decimal_to_paise(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

    @staticmethod
    def fresh_key():
        return uuid.uuid4()
