from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from core.models import Invoice, InvoiceLine, InvoiceLineTax, Payment, Subscription


class SeedScaleCommandTests(TestCase):
    def setUp(self):
        User.objects.create_user("admin@brightloop.test", "ValidPassword!", role=User.Role.ADMIN)
        User.objects.create_user("customer@brightloop.test", "ValidPassword!", role=User.Role.CUSTOMER)

    def test_fixture_has_related_financial_rows_and_repeat_is_safe(self):
        output = StringIO()
        call_command("seed_scale", subscriptions=8, stdout=output)
        self.assertEqual(Subscription.objects.filter(number__startswith="SCALE-SUB-").count(), 8)
        self.assertEqual(Invoice.objects.filter(number__startswith="SCALE-INV-").count(), 8)
        self.assertEqual(InvoiceLine.objects.filter(invoice__number__startswith="SCALE-INV-").count(), 8)
        self.assertEqual(InvoiceLineTax.objects.filter(invoice_line__invoice__number__startswith="SCALE-INV-").count(), 8)
        self.assertEqual(Payment.objects.filter(invoice__number__startswith="SCALE-INV-").count(), 4)
        self.assertEqual(Invoice.objects.filter(status=Invoice.Status.PAID, number__startswith="SCALE-INV-").count(), 2)
        second = StringIO()
        call_command("seed_scale", subscriptions=8, stdout=second)
        self.assertEqual(Subscription.objects.filter(number__startswith="SCALE-SUB-").count(), 8)
        self.assertIn("added=0 subscriptions", second.getvalue())
