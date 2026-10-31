from django.contrib import messages
from django.contrib.auth import login
from django import forms
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import (
    BrightloopPasswordResetForm,
    BrightloopSetPasswordForm,
    EmailAuthenticationForm,
    SignupForm,
)


def index(request):
    if request.user.is_authenticated:
        return redirect("insights:dashboard")
    return redirect("accounts:login")


class EmailLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class PostOnlyLogoutView(LogoutView):
    http_method_names = ["post", "options"]


def signup(request):
    if request.user.is_authenticated:
        return redirect("insights:dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.create_account()
        except forms.ValidationError as error:
            form.add_error("email", error)
        else:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Your customer account is ready.")
            return redirect("portal:dashboard")
    return render(request, "registration/signup.html", {"form": form})


class GenericPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    form_class = BrightloopPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")


class ResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class ResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    form_class = BrightloopSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class ResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"
