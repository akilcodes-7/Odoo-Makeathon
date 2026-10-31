"""Exercise the evaluator's real forms, persisted records and customer boundaries."""

from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import Customer, Invoice, Payment, Subscription


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EvaluationWorkflowTests(TestCase):
    password = "Evaluation!TestPassword"

    @classmethod
    def setUpTestData(cls):
        with patch.dict("os.environ", {"BRIGHTLOOP_DEMO_PASSWORD": cls.password}):
            call_command("seed_evaluation", noinput=True, stdout=StringIO())

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def post(self, url, data=None):
        data = dict(data or {})
        data["csrfmiddlewaretoken"] = self.client.cookies["csrftoken"].value
        return self.client.post(url, data)

    def sign_in(self, email):
        self.client = Client(enforce_csrf_checks=True)
        self.client.get(reverse("accounts:login"))
        response = self.post(reverse("accounts:login"), {"email": email, "password": self.password})
        self.assertEqual(response.status_code, 302)

    def test_quote_to_paid_invoice_with_login_csrf_email_and_customer_isolation(self):
        self.sign_in("staff@brightloop.test")
        subscription = Subscription.objects.get(number="EVAL-READY")
        for action, status in (("quote", "QUOTATION"), ("confirm", "CONFIRMED"), ("activate", "ACTIVE")):
            response = self.post(reverse("subscriptions:action", args=[subscription.pk, action]))
            self.assertEqual(response.status_code, 302)
            subscription.refresh_from_db()
            self.assertEqual(subscription.status, status)

        self.assertEqual(self.post(reverse("billing:run")).status_code, 302)
        invoice = subscription.invoices.get()
        self.assertEqual(invoice.status, Invoice.Status.DRAFT)
        self.post(reverse("billing:run"))
        self.assertEqual(subscription.invoices.count(), 1)
        self.post(reverse("finance:invoice_action", args=[invoice.pk, "confirm"]))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.CONFIRMED)

        self.post(reverse("finance_delivery:send", args=[invoice.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [invoice.customer_email])
        first = invoice.total_paise // 2
        for amount in (first, invoice.total_paise - first):
            response = self.post(reverse("finance_payments:new", args=[invoice.pk]), {
                "amount": f"{amount // 100}.{amount % 100:02d}",
                "method": Payment.Method.BANK, "paid_on": timezone.localdate().isoformat(),
                "note": "Evaluator workflow", "idempotency_key": str(uuid4()),
            })
            self.assertEqual(response.status_code, 302)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(sum(invoice.payments.values_list("amount_paise", flat=True)), invoice.total_paise)

        self.sign_in("customer@brightloop.test")
        self.assertContains(self.client.get(reverse("portal:invoice_detail", args=[invoice.pk])), invoice.number)
        self.assertEqual(self.client.get(reverse("finance_delivery:print", args=[invoice.pk])).status_code, 200)
        self.sign_in("customer2@brightloop.test")
        self.assertEqual(self.client.get(reverse("portal:invoice_detail", args=[invoice.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("finance_delivery:print", args=[invoice.pk])).status_code, 404)

    def test_customer_renewal_and_pause_resume_are_available_in_seeded_examples(self):
        self.sign_in("customer2@brightloop.test")
        subscription = Subscription.objects.get(number="EVAL-RENEW")
        detail = self.client.get(reverse("portal:subscription_detail", args=[subscription.pk]))
        self.assertContains(detail, "Request renewal")
        url = reverse("portal:subscription_action", args=[subscription.pk, "renew"])
        self.post(url)
        self.post(url)
        self.assertEqual(Subscription.objects.filter(renewed_from=subscription).count(), 1)
        self.assertEqual(subscription.successor.status, Subscription.Status.DRAFT)
        self.assertGreater(subscription.successor.start_date, subscription.expiry_date)

        self.sign_in("customer@brightloop.test")
        paused = Subscription.objects.get(number="EVAL-PAUSE")
        self.assertTrue(paused.is_paused)
        self.post(reverse("portal:subscription_action", args=[paused.pk, "resume"]))
        paused.refresh_from_db()
        self.assertFalse(paused.is_paused)

    def test_new_customer_and_staff_accounts_can_sign_in(self):
        self.client.get(reverse("accounts:signup"))
        response = self.post(reverse("accounts:signup"), {
            "email": "new-evaluator@example.test", "display_name": "New evaluator",
            "password1": self.password, "password2": self.password, "role": "ADMIN",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="new-evaluator@example.test")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(Customer.objects.filter(user=user).exists())
        self.sign_in(user.email)
        self.assertEqual(self.client.get(reverse("portal:dashboard")).status_code, 200)

        self.sign_in("admin@brightloop.test")
        self.assertContains(self.client.get(reverse("team:list")), "Team accounts")
        response = self.post(reverse("team:new"), {
            "email": "new-staff@example.test", "first_name": "New", "last_name": "Staff",
            "password1": self.password, "password2": self.password,
        })
        self.assertEqual(response.status_code, 302)
        self.sign_in("new-staff@example.test")
        self.assertEqual(self.client.get(reverse("subscriptions:list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("team:list")).status_code, 403)

    def test_demo_reseed_keeps_existing_accounts_and_evaluator_records(self):
        subscription = Subscription.objects.get(number="EVAL-READY")
        self.sign_in("staff@brightloop.test")
        self.post(reverse("subscriptions:action", args=[subscription.pk, "quote"]))
        counts = [model.objects.count() for model in (User, Subscription, Invoice, Payment)]
        with patch.dict("os.environ", {"BRIGHTLOOP_DEMO_PASSWORD": "Different!TestPassword"}):
            call_command("seed_evaluation", noinput=True, stdout=StringIO())
        self.assertEqual(counts, [model.objects.count() for model in (User, Subscription, Invoice, Payment)])
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.Status.QUOTATION)
        self.assertTrue(User.objects.get(email="staff@brightloop.test").check_password(self.password))
