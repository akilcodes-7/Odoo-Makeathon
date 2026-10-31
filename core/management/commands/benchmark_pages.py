"""Measure authenticated local Django routes and record request query counts."""

import platform
import statistics
import time

import django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from core.models import Customer, Invoice, Subscription


class Command(BaseCommand):
    help = "Measure dashboard, subscription, invoice, customer, and portal requests locally."

    def add_arguments(self, parser):
        parser.add_argument("--warm-samples", type=int, default=10)

    def handle(self, *args, **options):
        count = options["warm_samples"]
        if count < 1:
            raise CommandError("--warm-samples must be positive.")
        User = get_user_model()
        admin = User.objects.filter(email__iexact="admin@brightloop.test").first()
        customer_user = User.objects.filter(email__iexact="customer@brightloop.test").first()
        customer = Customer.objects.filter(user=customer_user).first() if customer_user else None
        if not admin or not customer_user or not customer:
            raise CommandError("Run seed_demo before benchmarking authenticated routes.")

        routes = [
            ("dashboard", "/", admin),
            ("subscriptions", "/subscriptions/", admin),
            ("invoices", "/invoices/", admin),
            ("customer detail", f"/customers/{customer.pk}/", admin),
            ("portal", "/portal/", customer_user),
        ]
        self.stdout.write(
            f"Environment: OS={platform.platform()}; Python={platform.python_version()}; "
            f"Django={django.get_version()}; database={connection.vendor}; "
            f"subscriptions={Subscription.objects.count()}; invoices={Invoice.objects.count()}; "
            f"warm_samples={count}; backend only (browser rendering not measured)."
        )
        failures = 0
        for label, path, user in routes:
            # Match the application's local host allowlist rather than the
            # test client's default `testserver` host.
            client = Client(HTTP_HOST="localhost")
            client.force_login(user)
            with CaptureQueriesContext(connection) as cold_queries:
                start = time.perf_counter()
                response = client.get(path)
                cold_seconds = time.perf_counter() - start
            if response.status_code != 200:
                failures += 1
                self.stdout.write(self.style.ERROR(
                    f"{label}: HTTP {response.status_code}; cold={cold_seconds:.4f}s; "
                    f"queries={len(cold_queries)}"
                ))
                continue
            warm_times = []
            warm_query_counts = []
            for _ in range(count):
                with CaptureQueriesContext(connection) as warm_queries:
                    start = time.perf_counter()
                    warm_response = client.get(path)
                    warm_times.append(time.perf_counter() - start)
                warm_query_counts.append(len(warm_queries))
                if warm_response.status_code != 200:
                    failures += 1
                    self.stdout.write(self.style.ERROR(f"{label}: warm request returned HTTP {warm_response.status_code}."))
                    break
            self.stdout.write(
                f"{label}: path={path}; role={user.role}; HTTP={response.status_code}; "
                f"cold={cold_seconds:.4f}s/{len(cold_queries)} queries; "
                f"warm_queries_median={statistics.median(warm_query_counts):g}; "
                f"warm_median={statistics.median(warm_times):.4f}s; "
                f"warm_max={max(warm_times):.4f}s; target<2s="
                f"{'PASS' if max([cold_seconds, *warm_times]) < 2 else 'FAIL'}"
            )
        if failures:
            raise CommandError(f"{failures} route request(s) failed.")
