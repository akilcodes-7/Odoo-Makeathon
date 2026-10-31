from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.services.billing import run_due_billing


class Command(BaseCommand):
    help = "Create due recurring invoices in bounded, repeatable batches."

    def add_arguments(self, parser):
        parser.add_argument("--as-of", help="Simulated date (YYYY-MM-DD); intended for local demo/tests.")
        parser.add_argument("--max-periods-per-subscription", type=int, default=24)
        parser.add_argument("--max-batches", type=int, default=100)

    def handle(self, *args, **options):
        as_of = timezone.localdate()
        if options["as_of"]:
            try:
                as_of = date.fromisoformat(options["as_of"])
            except ValueError as exc:
                raise CommandError("--as-of must use YYYY-MM-DD.") from exc
        max_periods = options["max_periods_per_subscription"]
        max_batches = options["max_batches"]
        if max_periods < 1 or max_batches < 1:
            raise CommandError("Batch limits must be positive integers.")
        created = existing = batches = 0
        errors = []
        remaining = 0
        while batches < max_batches:
            batches += 1
            result = run_due_billing(as_of=as_of, max_periods_per_subscription=max_periods)
            created += len(result.created_ids)
            existing += len(result.existing_ids)
            remaining = result.remaining_due_count
            errors.extend(result.errors)
            if errors or remaining == 0 or (not result.created_ids and not result.existing_ids):
                break
        self.stdout.write(
            f"Billing report: created={created}, existing={existing}, errors={len(errors)}, "
            f"remaining_due={remaining}, batches={batches}, as_of={as_of.isoformat()}"
        )
        for error in errors:
            self.stderr.write(f"ERROR: {error}")
        if remaining:
            self.stdout.write("Backlog remains; run the command again after resolving errors or raise the batch cap.")
