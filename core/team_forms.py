from django import forms
from django.db import IntegrityError, transaction

from accounts.managers import normalize_email_address
from accounts.models import User
from accounts.validators import validate_brightloop_password


class StaffCreationForm(forms.Form):
    email = forms.EmailField(max_length=254, widget=forms.EmailInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    password1 = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"class": "form-control"}))
    password2 = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean_email(self):
        email = normalize_email_address(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_brightloop_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2") and cleaned["password1"] != cleaned["password2"]:
            self.add_error("password2", "The passwords do not match.")
        return cleaned

    def create_user(self):
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=self.cleaned_data["email"],
                    password=self.cleaned_data["password1"],
                    first_name=self.cleaned_data["first_name"].strip(),
                    last_name=self.cleaned_data["last_name"].strip(),
                    role=User.Role.STAFF,
                )
        except IntegrityError as exc:
            raise forms.ValidationError("An account with this email already exists.") from exc
