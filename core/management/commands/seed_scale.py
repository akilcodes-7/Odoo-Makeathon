"""Idempotently add a local, recognizable scale dataset for query checks."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.models import (
    Customer, Invoice, InvoiceLine, InvoiceLineTax, Payment, Plan, Product,
    Subscription, SubscriptionLine, Tax,
)


class Command(BaseCommand):
    help = "Add deterministic SCALE-* subscriptions and related invoice/payment data."

    def add_arguments(self, parser):
        parser.add_argument("--subscriptions", type=int, default=5000)

    @transaction.atomic
    def handle(self, *args, **options):
        requested = options["subscriptions"]
        if requested < 1:
            raise CommandError("--subscriptions must be a positive integer.")
        demo_user = User.objects.filter(email__iexact="customer@brightloop.test", role=User.Role.CUSTOMER).first()
        staff_user = User.objects.filter(email__iexact="admin@brightloop.test", role=User.Role.ADMIN).first()
        if not demo_user or not staff_user:
            raise CommandError("Run seed_demo first; the scale fixture uses its local customer and admin accounts.")

        customer, _ = Customer.objects.get_or_create(
            user=demo_user,
            defaults={"display_name": "Demo Customer", "billing_email": demo_user.email},
        )
        customers = [customer]
        for index in range(1, 50):
            other, _ = Customer.objects.get_or_create(
                display_name=f"Scale Customer {index:02d}",
                defaults={"billing_email": f"scale-customer-{index:02d}@brightloop.test"},
            )
            customers.append(other)

        product, _ = Product.objects.get_or_create(
            name="Scale Demo Workspace",
            defaults={"type": Product.Type.SOFTWARE, "sales_price_paise": 10_000, "cost_price_paise": 2_000},
        )
        tax, _ = Tax.objects.get_or_create(name="Scale GST 18%", defaults={"rate_bps": 1_800})
        plan, _ = Plan.objects.get_or_create(
            name="Scale Demo Monthly",
            defaults={
                "primary_product": product, "price_paise": 10_000,
                "period": Plan.Period.MONTHLY, "min_quantity": 1,
                "available_from": timezone.localdate() - timedelta(days=365),
                "closable": True, "pausable": True, "renewable": True,
            },
        )
        if plan.primary_product_id != product.pk or plan.period != Plan.Period.MONTHLY:
            raise CommandError("Existing Scale Demo Monthly plan has incompatible terms; fixture was not changed.")

        existing_numbers = set(
            Subscription.objects.filter(number__startswith="SCALE-SUB-").values_list("number", flat=True)
        )
        missing = [index for index in range(1, requested + 1) if f"SCALE-SUB-{index:06d}" not in existing_numbers]
        today = timezone.localdate()
        new_subscriptions = [
            Subscription(
                number=f"SCALE-SUB-{index:06d}", customer=customers[(index - 1) % len(customers)],
                plan=plan, status=Subscription.Status.ACTIVE,
                start_date=today - timedelta(days=60), expiry_date=today + timedelta(days=365),
                billing_anchor_date=today - timedelta(days=60), billing_period_index=2,
                next_invoice_date=today, billing_period=Plan.Period.MONTHLY,
                auto_close_snapshot=False, closable_snapshot=True, pausable_snapshot=True,
                renewable_snapshot=True, min_quantity_snapshot=1,
            )
            for index in missing
        ]
        Subscription.objects.bulk_create(new_subscriptions, batch_size=500)

        lines = [
            SubscriptionLine(
                subscription=sub, product=product, is_primary=True, description=product.name,
                quantity=1, unit_price_paise=10_000, position=0,
            )
            for sub in new_subscriptions
        ]
        created_lines = SubscriptionLine.objects.bulk_create(lines, batch_size=500)
        through = SubscriptionLine.taxes.through
        through.objects.bulk_create(
            [through(subscriptionline_id=line.pk, tax_id=tax.pk) for line in created_lines], batch_size=500,
        )

        invoices = []
        for sub, line in zip(new_subscriptions, created_lines):
            invoices.append(Invoice(
                number=f"SCALE-INV-{int(sub.number[-6:]):06d}", subscription=sub,
                period_start=today - timedelta(days=30), period_end=today,
                invoice_date=today - timedelta(days=30), due_date=today - timedelta(days=15),
                status=Invoice.Status.PAID if int(sub.number[-6:]) % 4 == 0 else Invoice.Status.CONFIRMED,
                customer_name=sub.customer.display_name, customer_email=sub.customer.billing_email,
                customer_address=sub.customer.billing_address,
                subtotal_paise=10_000, discount_paise=0, tax_paise=1_800, total_paise=11_800,
                terms_days_snapshot=0, created_by=staff_user,
            ))
        created_invoices = Invoice.objects.bulk_create(invoices, batch_size=500)
        created_invoice_lines = InvoiceLine.objects.bulk_create([
            InvoiceLine(
                invoice=invoice, source_line=line, product_name=product.name,
                quantity=1, unit_price_paise=10_000, period_numerator_days=30,
                period_denominator_days=30, subtotal_paise=10_000, discount_paise=0,
                taxable_paise=10_000, tax_paise=1_800, total_paise=11_800, position=0,
            )
            for invoice, line in zip(created_invoices, created_lines)
        ], batch_size=500)
        InvoiceLineTax.objects.bulk_create([
            InvoiceLineTax(invoice_line=line, source_tax=tax, tax_name=tax.name, rate_bps=1_800, amount_paise=1_800)
            for line in created_invoice_lines
        ], batch_size=500)

        payments = []
        for invoice in created_invoices:
            index = int(invoice.number[-6:])
            if index % 4 == 0:
                amount = 11_800
            elif index % 4 == 1:
                amount = 5_900
            else:
                continue
            payments.append(Payment(
                invoice=invoice, method=Payment.Method.BANK, amount_paise=amount,
                paid_on=today - timedelta(days=1), note="Local scale fixture", created_by=staff_user,
            ))
        Payment.objects.bulk_create(payments, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f"Scale fixture: requested={requested}; added={len(new_subscriptions)} subscriptions, "
            f"{len(created_invoices)} invoices, {len(payments)} payments; existing scale rows were preserved."
        ))
