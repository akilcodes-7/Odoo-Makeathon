from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.db import IntegrityError, transaction

from core.models import Customer

from .managers import normalize_email_address
from .models import User
from .validators import validate_brightloop_password


def _style_fields(form):
    for field in form.fields.values():
        field.widget.attrs.setdefault("class", "form-control")


class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(label="Email address", max_length=254)
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput)

    error_messages = {"invalid_login": "Email or password is incorrect."}

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        _style_fields(self)

    def clean_email(self):
        return normalize_email_address(self.cleaned_data["email"])

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("email") and cleaned.get("password"):
            self.user_cache = authenticate(
                self.request, username=cleaned["email"], password=cleaned["password"]
            )
            if self.user_cache is None:
                raise forms.ValidationError(self.error_messages["invalid_login"], code="invalid_login")
        return cleaned

    def get_user(self):
        return self.user_cache


class SignupForm(forms.Form):
    email = forms.EmailField(max_length=254)
    display_name = forms.CharField(max_length=200, label="Your name")
    password1 = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

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

    def create_account(self):
        """Create a customer identity and profile as one transaction."""
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=self.cleaned_data["email"],
                    password=self.cleaned_data["password1"],
                    first_name=self.cleaned_data["display_name"].strip(),
                    role=User.Role.CUSTOMER,
                )
                Customer.objects.create(
                    user=user,
                    display_name=self.cleaned_data["display_name"].strip(),
                    billing_email=user.email,
                )
                return user
        except IntegrityError:
            # The inner atomic block has rolled back, so the outer request can
            # safely render a useful duplicate-address validation error.
            raise forms.ValidationError("An account with this email already exists.")


class BrightloopPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    def clean_email(self):
        return normalize_email_address(self.cleaned_data["email"])


class BrightloopSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)

    def clean_new_password1(self):
        password = self.cleaned_data["new_password1"]
        validate_brightloop_password(password)
        return password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The passwords do not match.", code="password_mismatch")
        return password2
