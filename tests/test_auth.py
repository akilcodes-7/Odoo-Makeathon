from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.forms import SignupForm
from accounts.validators import validate_brightloop_password
from core.models import Customer


User = get_user_model()


class AuthenticationFlowTests(TestCase):
    def test_case_insensitive_email_uniqueness_and_normalization(self):
        first = User.objects.create_user("Alice@Example.com", "LongEnough!a")
        self.assertEqual(first.email, "alice@example.com")
        form = SignupForm(
            data={
                "email": "ALICE@example.com",
                "display_name": "Alice",
                "password1": "ValidPass!9",
                "password2": "ValidPass!9",
                "role": "ADMIN",
                "is_staff": "on",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_signup_ignores_role_and_creates_customer_atomically(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": " Alice@Example.com ",
                "display_name": "Alice Example",
                "password1": "ValidPass!9",
                "password2": "ValidPass!9",
                "role": "ADMIN",
                "is_staff": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="alice@example.com")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.customer_profile.display_name, "Alice Example")
        self.assertEqual(user.customer_profile.billing_email, user.email)

    def test_exact_password_rule(self):
        with self.assertRaises(ValidationError):
            validate_brightloop_password("Ab!12345")
        validate_brightloop_password("Abcdefg!h")
        for password in ("lowercase!9", "UPPERCASE!9", "NoSpecial99"):
            with self.subTest(password=password), self.assertRaises(ValidationError):
                validate_brightloop_password(password)

    def test_login_normalizes_email(self):
        User.objects.create_user("person@example.com", "ValidPass!9")
        response = self.client.post(
            reverse("accounts:login"),
            {"email": " PERSON@Example.com ", "password": "ValidPass!9"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_reset_acknowledges_unknown_email_and_token_is_one_use(self):
        unknown = self.client.post(
            reverse("accounts:password_reset"), {"email": "nobody@example.com"}
        )
        self.assertRedirects(unknown, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

        user = User.objects.create_user("person@example.com", "ValidPass!9")
        self.client.post(reverse("accounts:password_reset"), {"email": "PERSON@example.com"})
        self.assertEqual(len(mail.outbox), 1)
        path = mail.outbox[0].body.split("\n")
        reset_path = next(line for line in path if "/accounts/password-reset/" in line)
        reset_path = reset_path.split("http://testserver", 1)[-1]
        response = self.client.get(reset_path)
        self.assertEqual(response.status_code, 302)
        reset_path = response["Location"]
        response = self.client.get(reset_path)
        self.assertEqual(response.status_code, 200)
        confirm_path = reset_path
        response = self.client.post(
            confirm_path,
            {"new_password1": "ChangedPass!9", "new_password2": "ChangedPass!9"},
        )
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        response = self.client.get(confirm_path)
        self.assertContains(response, "invalid or has already been used")

    def test_logout_is_post_only_and_csrf_protected(self):
        user = User.objects.create_user("person@example.com", "ValidPass!9")
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        self.assertEqual(client.get(reverse("accounts:logout")).status_code, 405)
        self.assertEqual(client.post(reverse("accounts:logout")).status_code, 403)
        response = client.get(reverse("accounts:password_reset"))
        self.assertEqual(response.status_code, 200)
        csrf = response.cookies["csrftoken"].value
        response = client.post(reverse("accounts:logout"), {"csrfmiddlewaretoken": csrf}, HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", client.session)


class CustomerIdentityTests(TestCase):
    def test_foreign_customer_filter_scopes_queryset(self):
        own_user = User.objects.create_user("own@example.com", "ValidPass!9")
        other_user = User.objects.create_user("other@example.com", "ValidPass!9")
        own = Customer.objects.create(user=own_user, display_name="Own", billing_email=own_user.email)
        Customer.objects.create(user=other_user, display_name="Other", billing_email=other_user.email)
        from accounts.permissions import customer_owned

        self.assertQuerySetEqual(customer_owned(Customer.objects.all(), own_user), [own], transform=lambda row: row)
