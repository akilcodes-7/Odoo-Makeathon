from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.models import User
from core.models import Customer, Invoice, Subscription
from .selectors import (
    customer_scope, dashboard_summary, overdue_invoices,
    scoped_invoices, scoped_subscriptions,
)


SUBSCRIPTION_SORTS = {
    "newest": ("-created_at", "-pk"),
    "oldest": ("created_at", "pk"),
    "customer": ("customer__display_name", "pk"),
    "expiry": ("expiry_date", "pk"),
}
INVOICE_SORTS = {
    "newest": ("-invoice_date", "-pk"),
    "oldest": ("invoice_date", "pk"),
    "due": ("due_date", "pk"),
    "amount": ("-total_paise", "-pk"),
}


def _date_value(raw, label, fallback):
    if raw in (None, ""):
        return fallback
    try:
        return date.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Enter a valid {label} date (YYYY-MM-DD).") from exc


def _filters(request, *, today):
    first_of_month = today.replace(day=1)
    start_date = _date_value(request.GET.get("start"), "start", first_of_month)
    end_date = _date_value(request.GET.get("end"), "end", today)
    if start_date > end_date:
        raise ValueError("The start date must be on or before the end date.")

    customer_id = customer_scope(request.user, requested_customer=request.GET.get("customer", ""))
    sub_status = request.GET.get("subscription_status", "")
    invoice_status = request.GET.get("invoice_status", "")
    if sub_status and sub_status not in Subscription.Status.values:
        raise ValueError("Choose a valid subscription status.")
    if invoice_status and invoice_status not in Invoice.Status.values:
        raise ValueError("Choose a valid invoice status.")
    sub_sort = request.GET.get("subscription_sort", "newest")
    invoice_sort = request.GET.get("invoice_sort", "newest")
    if sub_sort not in SUBSCRIPTION_SORTS or invoice_sort not in INVOICE_SORTS:
        raise ValueError("Choose a valid sort order.")
    return {
        "start_date": start_date,
        "end_date": end_date,
        "customer_id": customer_id,
        "subscription_status": sub_status,
        "invoice_status": invoice_status,
        "subscription_sort": sub_sort,
        "invoice_sort": invoice_sort,
        "search": request.GET.get("q", "").strip()[:100],
    }


def _json_summary(user, filters, today):
    summary = dashboard_summary(
        user,
        customer_id=filters["customer_id"],
        start_date=filters["start_date"],
        end_date=filters["end_date"],
        as_of=today,
    )
    summary["collection_days"] = [
        {**row, "paid_on": row["paid_on"].isoformat()} for row in summary["collection_days"]
    ]
    summary["as_of"] = summary["as_of"].isoformat()
    summary["range_start"] = summary["range_start"].isoformat()
    summary["range_end"] = summary["range_end"].isoformat()
    return summary


@login_required
def summary_api(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET required."}, status=405)
    today = timezone.localdate()
    try:
        filters = _filters(request, today=today)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(_json_summary(request.user, filters, today))


@login_required
def index(request):
    today = timezone.localdate()
    try:
        filters = _filters(request, today=today)
    except ValueError as exc:
        return render(request, "insights/dashboard.html", {
            "error": str(exc), "customers": [], "summary": None,
        }, status=400)

    user = request.user
    customer_id = filters["customer_id"]
    summary = dashboard_summary(
        user, customer_id=customer_id,
        start_date=filters["start_date"], end_date=filters["end_date"], as_of=today,
    )
    subscriptions = scoped_subscriptions(user, customer_id).select_related("customer", "plan")
    invoices = scoped_invoices(user, customer_id).select_related("subscription", "subscription__customer")
    if user.role == User.Role.CUSTOMER:
        invoices = invoices.filter(status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID))
    if filters["subscription_status"]:
        subscriptions = subscriptions.filter(status=filters["subscription_status"])
    if filters["invoice_status"]:
        invoices = invoices.filter(status=filters["invoice_status"])
    if filters["search"]:
        search = filters["search"]
        subscriptions = subscriptions.filter(
            Q(number__icontains=search) | Q(customer__display_name__icontains=search) | Q(plan__name__icontains=search)
        )
        invoices = invoices.filter(
            Q(number__icontains=search) | Q(customer_name__icontains=search) | Q(subscription__number__icontains=search)
        )
    subscriptions_page = Paginator(subscriptions.order_by(*SUBSCRIPTION_SORTS[filters["subscription_sort"]]), 25).get_page(request.GET.get("page"))
    invoices_page = Paginator(invoices.order_by(*INVOICE_SORTS[filters["invoice_sort"]]), 25).get_page(request.GET.get("page"))
    overdue_page = Paginator(
        overdue_invoices(user, customer_id, as_of=today).order_by("due_date", "pk"), 10
    ).get_page(request.GET.get("overdue_page"))

    params = request.GET.copy()
    params.pop("page", None)
    params.pop("overdue_page", None)
    query_string = params.urlencode()
    customers = Customer.objects.order_by("display_name", "pk") if user.role in (User.Role.ADMIN, User.Role.STAFF) else []
    return render(request, "insights/dashboard.html", {
        "summary": summary,
        "today": today,
        "filters": filters,
        "customers": customers,
        "subscriptions_page": subscriptions_page,
        "invoices_page": invoices_page,
        "overdue_page": overdue_page,
        "query_string": query_string,
        "subscription_statuses": Subscription.Status.choices,
        "invoice_statuses": Invoice.Status.choices,
        "collection_days": summary["collection_days"],
    })
