"""Idempotently create local-only admin, staff and customer demo accounts."""

import getpass
import os
import re

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from core.models import Customer


DEMO_ACCOUNTS = (
    ("admin@brightloop.test", User.Role.ADMIN, "Demo", "Admin"),
    ("staff@brightloop.test", User.Role.STAFF, "Demo", "Staff"),
    ("customer@brightloop.test", User.Role.CUSTOMER, "Demo", "Customer"),
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
    help = "Create the local Brightloop demo admin, staff and customer accounts."

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

                customer_email, _role, first_name, last_name = DEMO_ACCOUNTS[2]
                customer_user = resolved[customer_email]
                Customer.objects.get_or_create(
                    user=customer_user,
                    defaults={
                        "display_name": f"{first_name} {last_name}",
                        "billing_email": customer_email,
                    },
                )
        except CommandError:
            raise
        except Exception as error:
            raise CommandError(
                "Demo accounts could not be created; no partial changes were kept. "
                f"Resolve the conflict and retry ({error.__class__.__name__})."
            ) from error

        self.stdout.write(self.style.SUCCESS("Demo accounts are ready."))
        self.stdout.write("Admin: admin@brightloop.test")
        self.stdout.write("Staff: staff@brightloop.test")
        self.stdout.write("Customer: customer@brightloop.test")
        self.stdout.write(f"Created: {len(created)}; already present: {len(existing)}.")
        self.stdout.write(
            "All accounts share the local password supplied by you; it was not printed."
        )

