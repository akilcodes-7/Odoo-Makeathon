"""Idempotently create local-only admin, staff, customer accounts and representative demo data."""

import getpass
import os
import re
import uuid
from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.models import (
    Customer, Discount, Invoice, Payment, Plan, Product, ProductVariant,
    QuoteTemplate, QuoteTemplateLine, Subscription, SubscriptionLine, Tax,
)
from core.services.billing import run_due_billing
from core.services.lifecycle import transition_invoice, transition_subscription
from finance.services.payments import record_payment


DEMO_ACCOUNTS = (
    ("admin@brightloop.test", User.Role.ADMIN, "Demo", "Admin"),
    ("staff@brightloop.test", User.Role.STAFF, "Demo", "Staff"),
    ("customer@brightloop.test", User.Role.CUSTOMER, "Acme", "Customer"),
    ("customer2@brightloop.test", User.Role.CUSTOMER, "Globex", "Customer"),
)


def validate_demo_password(password: str, *, user: User | None = None) -> None:
    """Apply the brief's password rule before creating local demo credentials."""
    if len(password) < 9:
        raise CommandError("The demo password must have at least 9 characters.")
    if not re.search(r"[A-Z]", password):
        raise CommandError("The demo password must contain an uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise CommandError("The demo password must contain a lowercase letter.")
    if not re.search(r"[^A-Za-z0-9\s]", password):
        raise CommandError("The demo password must contain a special character.")
    if password.isspace():
        raise CommandError("The demo password cannot be only whitespace.")
    if user is not None:
        validate_password(password, user=user)


class Command(BaseCommand):
    help = "Create the local Brightloop demo accounts and representative catalog, subscription, and invoice demo data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput", "--no-input",
            action="store_true",
            help="Do not prompt for input. Uses BRIGHTLOOP_DEMO_PASSWORD environment variable.",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Update existing demo accounts to use the supplied password.",
        )

    def _password(self, *, interactive: bool) -> str:
        value = os.environ.get("BRIGHTLOOP_DEMO_PASSWORD")
        if value:
            return value
        if not interactive:
            raise CommandError(
                "Set BRIGHTLOOP_DEMO_PASSWORD to a local-only value before running "
                "this command non-interactively. Do not commit or share that password."
            )
        first = getpass.getpass("Choose a local demo password (9+ chars, upper/lower/special): ")
        second = getpass.getpass("Confirm the local demo password: ")
        if first != second:
            raise CommandError("The demo password entries did not match.")
        return first

    def handle(self, *args, **options):
        interactive = not options.get("noinput", False)
        reset_passwords = options.get("reset_passwords", False)
        password = self._password(interactive=interactive)
        for email, _role, first_name, _last_name in DEMO_ACCOUNTS:
            validate_demo_password(password, user=User(email=email, first_name=first_name))

        created = []
        existing = []
        try:
            with transaction.atomic():
                resolved: dict[str, User] = {}
                for email, role, first_name, last_name in DEMO_ACCOUNTS:
                    user = User.objects.filter(email__iexact=email).first()
                    if user is not None:
                        if user.role != role:
                            raise CommandError(
                                f"{email} already exists with role {user.role}; "
                                "the seed command did not change it."
                            )
                        if role == User.Role.ADMIN and not user.is_superuser:
                            raise CommandError(
                                f"{email} exists but is not a Django superuser; "
                                "the seed command did not elevate it."
                            )
                        if reset_passwords:
                            user.set_password(password)
                            user.save()
                        resolved[email] = user
                        existing.append(email)
                        continue

                    fields = {"first_name": first_name, "last_name": last_name}
                    if role == User.Role.ADMIN:
                        user = User.objects.create_superuser(email, password, **fields)
                    else:
                        user = User.objects.create_user(
                            email, password, role=role, **fields
                        )
                    resolved[email] = user
                    created.append(email)

                # Seed representative demo data
                self._seed_data(resolved)

        except CommandError:
            raise
        except Exception as error:
            raise CommandError(
                "Demo data could not be created; no partial changes were kept. "
                f"Resolve the conflict and retry ({error.__class__.__name__}: {error})."
            ) from error

        self.stdout.write(self.style.SUCCESS("Demo accounts and representative data are ready."))
        self.stdout.write("Admin:     admin@brightloop.test")
        self.stdout.write("Staff:     staff@brightloop.test")
        self.stdout.write("Customer:  customer@brightloop.test (Acme Technologies)")
        self.stdout.write("Customer:  customer2@brightloop.test (Globex Corporation)")
        self.stdout.write(f"Accounts created: {len(created)}; already present: {len(existing)}.")
        self.stdout.write(
            "All accounts share the local password supplied by you; it was not printed."
        )

    def _seed_data(self, users: dict[str, User]):
        today = timezone.localdate()
        admin = users["admin@brightloop.test"]
        staff = users["staff@brightloop.test"]
        cust_user1 = users["customer@brightloop.test"]
        cust_user2 = users["customer2@brightloop.test"]

        # 1. Customers
        customer1, _ = Customer.objects.get_or_create(
            user=cust_user1,
            defaults={
                "display_name": "Acme Technologies Pvt Ltd",
                "billing_email": cust_user1.email,
                "billing_address": "Block 4, Tech Park, Whitefield, Bengaluru, KA 560066",
                "phone": "+91 98765 43210",
            },
        )
        customer2, _ = Customer.objects.get_or_create(
            user=cust_user2,
            defaults={
                "display_name": "Globex Corporation India",
                "billing_email": cust_user2.email,
                "billing_address": "42 Marine Lines, Nariman Point, Mumbai, MH 400021",
                "phone": "+91 91234 56789",
            },
        )

        # 2. Taxes
        gst, _ = Tax.objects.get_or_create(name="GST 18%", defaults={"rate_bps": 1800, "created_by": admin})
        cess, _ = Tax.objects.get_or_create(name="Service Tax 5%", defaults={"rate_bps": 500, "created_by": admin})

        # 3. Products
        cloud_suite, _ = Product.objects.get_or_create(
            name="Brightloop Cloud Suite",
            defaults={
                "type": Product.Type.SOFTWARE,
                "sales_price_paise": 120_000,
                "cost_price_paise": 30_000,
                "notes": "Core enterprise SaaS workspace platform.",
                "created_by": admin,
            },
        )
        support_247, _ = Product.objects.get_or_create(
            name="Priority 24/7 Support",
            defaults={
                "type": Product.Type.SERVICE,
                "sales_price_paise": 50_000,
                "cost_price_paise": 15_000,
                "notes": "24/7 priority support channel with 1-hour SLA.",
                "created_by": admin,
            },
        )
        fido_key, _ = Product.objects.get_or_create(
            name="Hardware Security Key",
            defaults={
                "type": Product.Type.ADDON,
                "sales_price_paise": 25_000,
                "cost_price_paise": 10_000,
                "notes": "FIDO2 physical WebAuthn security key.",
                "created_by": admin,
            },
        )

        # 4. Product Variants
        ProductVariant.objects.get_or_create(
            product=cloud_suite, attribute_name="Edition", attribute_value="Pro",
            defaults={"extra_price_paise": 30_000, "created_by": admin},
        )
        ProductVariant.objects.get_or_create(
            product=cloud_suite, attribute_name="Edition", attribute_value="Enterprise",
            defaults={"extra_price_paise": 80_000, "created_by": admin},
        )

        # 5. Plans across 4 periods
        plan_daily, _ = Plan.objects.get_or_create(
            name="Starter Daily Pass",
            defaults={
                "primary_product": cloud_suite,
                "price_paise": 10_000,
                "period": Plan.Period.DAILY,
                "min_quantity": 1,
                "available_from": today - timedelta(days=90),
                "closable": True, "pausable": False, "renewable": False, "auto_close": True,
                "created_by": admin,
            },
        )
        plan_weekly, _ = Plan.objects.get_or_create(
            name="Team Weekly",
            defaults={
                "primary_product": cloud_suite,
                "price_paise": 60_000,
                "period": Plan.Period.WEEKLY,
                "min_quantity": 1,
                "available_from": today - timedelta(days=90),
                "closable": True, "pausable": False, "renewable": True, "auto_close": False,
                "created_by": admin,
            },
        )
        plan_monthly, _ = Plan.objects.get_or_create(
            name="Professional Monthly",
            defaults={
                "primary_product": cloud_suite,
                "price_paise": 120_000,
                "period": Plan.Period.MONTHLY,
                "min_quantity": 1,
                "available_from": today - timedelta(days=120),
                "closable": True, "pausable": True, "renewable": True, "auto_close": False,
                "created_by": admin,
            },
        )
        plan_yearly, _ = Plan.objects.get_or_create(
            name="Enterprise Annual",
            defaults={
                "primary_product": cloud_suite,
                "price_paise": 1_200_000,
                "period": Plan.Period.YEARLY,
                "min_quantity": 1,
                "available_from": today - timedelta(days=180),
                "closable": True, "pausable": True, "renewable": True, "auto_close": True,
                "created_by": admin,
            },
        )

        # 6. Discounts
        disc_percent, _ = Discount.objects.get_or_create(
            name="Launch Offer 10%",
            defaults={
                "kind": Discount.Kind.PERCENT,
                "percent_bps": 1000,
                "scope": Discount.Scope.SUBSCRIPTION,
                "min_purchase_paise": 50_000,
                "starts_on": today - timedelta(days=60),
                "ends_on": today + timedelta(days=300),
                "max_uses": 100,
                "created_by": admin,
            },
        )
        disc_fixed, _ = Discount.objects.get_or_create(
            name="Welcome Flat ₹200",
            defaults={
                "kind": Discount.Kind.FIXED,
                "amount_paise": 20_000,
                "scope": Discount.Scope.SUBSCRIPTION,
                "min_purchase_paise": 100_000,
                "starts_on": today - timedelta(days=60),
                "ends_on": today + timedelta(days=300),
                "max_uses": 50,
                "created_by": admin,
            },
        )

        # 7. Quote Template
        template, created_tmpl = QuoteTemplate.objects.get_or_create(
            name="Standard SaaS Onboarding",
            defaults={
                "plan": plan_monthly,
                "validity_days": 14,
                "notes": "Pre-configured onboarding quotation with Cloud Suite + 24/7 Support.",
                "created_by": admin,
            },
        )
        if created_tmpl:
            line_pri = QuoteTemplateLine.objects.create(
                template=template,
                product=cloud_suite,
                is_primary=True,
                quantity=1,
                unit_price_paise=120_000,
                position=0,
            )
            line_pri.taxes.add(gst)
            line_supp = QuoteTemplateLine.objects.create(
                template=template,
                product=support_247,
                is_primary=False,
                quantity=1,
                unit_price_paise=50_000,
                position=1,
            )
            line_supp.taxes.add(gst)

        # 8. Representative Subscriptions & Invoices
        self._seed_subscriptions(today, staff, customer1, customer2, plan_monthly, plan_yearly, plan_weekly, plan_daily, cloud_suite, support_247, gst)

    def _seed_subscriptions(self, today, staff, customer1, customer2, plan_monthly, plan_yearly, plan_weekly, plan_daily, cloud_suite, support_247, gst):
        # Sub 1: Active Monthly subscription for Customer 1 (Acme)
        sub1 = Subscription.objects.filter(customer=customer1, plan=plan_monthly, status=Subscription.Status.ACTIVE).first()
        if not sub1:
            sub1 = Subscription.objects.create(
                number="SUB-TEMP",
                customer=customer1,
                plan=plan_monthly,
                start_date=today - timedelta(days=60),
                expiry_date=today + timedelta(days=120),
                payment_terms_days=15,
                billing_period=plan_monthly.period,
                billing_anchor_date=today - timedelta(days=60),
                billing_period_index=0,
                next_invoice_date=today - timedelta(days=60),
                auto_close_snapshot=plan_monthly.auto_close,
                closable_snapshot=plan_monthly.closable,
                pausable_snapshot=plan_monthly.pausable,
                renewable_snapshot=plan_monthly.renewable,
                min_quantity_snapshot=plan_monthly.min_quantity,
                created_by=staff,
            )
            sub1.number = f"SUB-{sub1.pk:06d}"
            sub1.save(update_fields=["number"])

            line1 = SubscriptionLine.objects.create(
                subscription=sub1,
                product=cloud_suite,
                is_primary=True,
                quantity=1,
                unit_price_paise=120_000,
                position=0,
            )
            line1.taxes.add(gst)
            line2 = SubscriptionLine.objects.create(
                subscription=sub1,
                product=support_247,
                is_primary=False,
                quantity=1,
                unit_price_paise=50_000,
                position=1,
            )
            line2.taxes.add(gst)

            transition_subscription(sub1.pk, Subscription.Status.QUOTATION, actor=staff)
            transition_subscription(sub1.pk, Subscription.Status.CONFIRMED, actor=staff)
            transition_subscription(sub1.pk, Subscription.Status.ACTIVE, actor=staff)

            # Bill periods up to today
            run_due_billing(as_of=today, subscription_ids=[sub1.pk], actor=staff)

            # Settle invoices
            invoices = list(sub1.invoices.order_by("invoice_date"))
            if len(invoices) >= 1:
                inv1 = invoices[0]
                if inv1.status == Invoice.Status.DRAFT:
                    transition_invoice(inv1.pk, Invoice.Status.CONFIRMED, actor=staff)
                record_payment(
                    inv1.pk,
                    amount_paise=inv1.total_paise,
                    method=Payment.Method.BANK,
                    paid_on=inv1.invoice_date,
                    note="Full bank wire settlement.",
                    idempotency_key=uuid.uuid4(),
                    actor=staff,
                )
            if len(invoices) >= 2:
                inv2 = invoices[1]
                if inv2.status == Invoice.Status.DRAFT:
                    transition_invoice(inv2.pk, Invoice.Status.CONFIRMED, actor=staff)
                # Partial payment of 50%
                record_payment(
                    inv2.pk,
                    amount_paise=inv2.total_paise // 2,
                    method=Payment.Method.CARD,
                    paid_on=inv2.invoice_date,
                    note="Initial card installment.",
                    idempotency_key=uuid.uuid4(),
                    actor=staff,
                )

        # Sub 2: Active Annual subscription for Customer 1 (Acme)
        sub2 = Subscription.objects.filter(customer=customer1, plan=plan_yearly, status=Subscription.Status.ACTIVE).first()
        if not sub2:
            sub2 = Subscription.objects.create(
                number="SUB-TEMP",
                customer=customer1,
                plan=plan_yearly,
                start_date=today - timedelta(days=15),
                expiry_date=today + timedelta(days=350),
                payment_terms_days=30,
                billing_period=plan_yearly.period,
                billing_anchor_date=today - timedelta(days=15),
                billing_period_index=0,
                next_invoice_date=today - timedelta(days=15),
                auto_close_snapshot=plan_yearly.auto_close,
                closable_snapshot=plan_yearly.closable,
                pausable_snapshot=plan_yearly.pausable,
                renewable_snapshot=plan_yearly.renewable,
                min_quantity_snapshot=plan_yearly.min_quantity,
                created_by=staff,
            )
            sub2.number = f"SUB-{sub2.pk:06d}"
            sub2.save(update_fields=["number"])

            line = SubscriptionLine.objects.create(
                subscription=sub2,
                product=cloud_suite,
                is_primary=True,
                quantity=2,
                unit_price_paise=1_200_000,
                position=0,
            )
            line.taxes.add(gst)

            transition_subscription(sub2.pk, Subscription.Status.QUOTATION, actor=staff)
            transition_subscription(sub2.pk, Subscription.Status.CONFIRMED, actor=staff)
            transition_subscription(sub2.pk, Subscription.Status.ACTIVE, actor=staff)

            run_due_billing(as_of=today, subscription_ids=[sub2.pk], actor=staff)
            inv = sub2.invoices.first()
            if inv and inv.status == Invoice.Status.DRAFT:
                transition_invoice(inv.pk, Invoice.Status.CONFIRMED, actor=staff)

        # Sub 3: Confirmed subscription for Customer 2 (Globex)
        sub3 = Subscription.objects.filter(customer=customer2, plan=plan_monthly, status=Subscription.Status.CONFIRMED).first()
        if not sub3:
            sub3 = Subscription.objects.create(
                number="SUB-TEMP",
                customer=customer2,
                plan=plan_monthly,
                start_date=today + timedelta(days=5),
                expiry_date=today + timedelta(days=185),
                payment_terms_days=15,
                billing_period=plan_monthly.period,
                billing_anchor_date=today + timedelta(days=5),
                billing_period_index=0,
                next_invoice_date=today + timedelta(days=5),
                auto_close_snapshot=plan_monthly.auto_close,
                closable_snapshot=plan_monthly.closable,
                pausable_snapshot=plan_monthly.pausable,
                renewable_snapshot=plan_monthly.renewable,
                min_quantity_snapshot=plan_monthly.min_quantity,
                created_by=staff,
            )
            sub3.number = f"SUB-{sub3.pk:06d}"
            sub3.save(update_fields=["number"])

            line = SubscriptionLine.objects.create(
                subscription=sub3,
                product=cloud_suite,
                is_primary=True,
                quantity=1,
                unit_price_paise=120_000,
                position=0,
            )
            line.taxes.add(gst)

            transition_subscription(sub3.pk, Subscription.Status.QUOTATION, actor=staff)
            transition_subscription(sub3.pk, Subscription.Status.CONFIRMED, actor=staff)

        # Sub 4: Quotation for Customer 2 (Globex)
        sub4 = Subscription.objects.filter(customer=customer2, plan=plan_weekly, status=Subscription.Status.QUOTATION).first()
        if not sub4:
            sub4 = Subscription.objects.create(
                number="SUB-TEMP",
                customer=customer2,
                plan=plan_weekly,
                start_date=today + timedelta(days=2),
                expiry_date=today + timedelta(days=30),
                payment_terms_days=7,
                billing_period=plan_weekly.period,
                billing_anchor_date=today + timedelta(days=2),
                billing_period_index=0,
                next_invoice_date=today + timedelta(days=2),
                auto_close_snapshot=plan_weekly.auto_close,
                closable_snapshot=plan_weekly.closable,
                pausable_snapshot=plan_weekly.pausable,
                renewable_snapshot=plan_weekly.renewable,
                min_quantity_snapshot=plan_weekly.min_quantity,
                created_by=staff,
            )
            sub4.number = f"SUB-{sub4.pk:06d}"
            sub4.save(update_fields=["number"])

            line = SubscriptionLine.objects.create(
                subscription=sub4,
                product=cloud_suite,
                is_primary=True,
                quantity=1,
                unit_price_paise=60_000,
                position=0,
            )
            line.taxes.add(gst)
            transition_subscription(sub4.pk, Subscription.Status.QUOTATION, actor=staff)

        # Sub 5: Draft subscription for Customer 1 (Acme)
        sub5 = Subscription.objects.filter(customer=customer1, plan=plan_daily, status=Subscription.Status.DRAFT).first()
        if not sub5:
            sub5 = Subscription.objects.create(
                number="SUB-TEMP",
                customer=customer1,
                plan=plan_daily,
                start_date=today,
                expiry_date=today + timedelta(days=14),
                payment_terms_days=7,
                billing_period=plan_daily.period,
                billing_anchor_date=today,
                billing_period_index=0,
                next_invoice_date=today,
                auto_close_snapshot=plan_daily.auto_close,
                closable_snapshot=plan_daily.closable,
                pausable_snapshot=plan_daily.pausable,
                renewable_snapshot=plan_daily.renewable,
                min_quantity_snapshot=plan_daily.min_quantity,
                created_by=staff,
            )
            sub5.number = f"SUB-{sub5.pk:06d}"
            sub5.save(update_fields=["number"])

            line = SubscriptionLine.objects.create(
                subscription=sub5,
                product=cloud_suite,
                is_primary=True,
                quantity=1,
                unit_price_paise=10_000,
                position=0,
            )
            line.taxes.add(gst)

        # Sub 6: Closed subscription for Customer 2 (Globex)
        sub6 = Subscription.objects.filter(customer=customer2, plan=plan_daily, status=Subscription.Status.CLOSED).first()
        if not sub6:
            sub6 = Subscription.objects.create(
                number="SUB-TEMP",
                customer=customer2,
                plan=plan_daily,
                start_date=today - timedelta(days=40),
                expiry_date=today - timedelta(days=20),
                payment_terms_days=7,
                billing_period=plan_daily.period,
                billing_anchor_date=today - timedelta(days=40),
                billing_period_index=0,
                next_invoice_date=today - timedelta(days=40),
                auto_close_snapshot=plan_daily.auto_close,
                closable_snapshot=plan_daily.closable,
                pausable_snapshot=plan_daily.pausable,
                renewable_snapshot=plan_daily.renewable,
                min_quantity_snapshot=plan_daily.min_quantity,
                created_by=staff,
            )
            sub6.number = f"SUB-{sub6.pk:06d}"
            sub6.save(update_fields=["number"])

            line = SubscriptionLine.objects.create(
                subscription=sub6,
                product=cloud_suite,
                is_primary=True,
                quantity=1,
                unit_price_paise=10_000,
                position=0,
            )
            line.taxes.add(gst)

            transition_subscription(sub6.pk, Subscription.Status.QUOTATION, actor=staff)
            transition_subscription(sub6.pk, Subscription.Status.CONFIRMED, actor=staff)
            transition_subscription(sub6.pk, Subscription.Status.CLOSED, actor=staff, reason="Trial period ended.")
