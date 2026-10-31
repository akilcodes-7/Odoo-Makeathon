from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from accounts.permissions import customer_owned, role_required
from core.models import Invoice, Payment, Subscription
from core.services.exceptions import DomainValidationError
from core.services.lifecycle import (
    pause_subscription,
    renew_subscription,
    resume_subscription,
    transition_subscription,
)


CUSTOMER_ROLE = (User.Role.CUSTOMER,)
PORTAL_INVOICE_STATUSES = (Invoice.Status.CONFIRMED, Invoice.Status.PAID)


def _own_subscriptions(user):
    return customer_owned(
        Subscription.objects.all(), user, customer_path="customer"
    ).select_related("customer", "plan")


def _own_invoices(user):
    # Restrict state and owner before any object lookup. Internal drafts and
    # cancelled invoices are deliberately invisible in the customer portal.
    return customer_owned(
        Invoice.objects.filter(status__in=PORTAL_INVOICE_STATUSES),
        user,
        customer_path="subscription__customer",
    ).select_related("subscription", "subscription__plan", "subscription__customer")


def _with_invoice_balances(queryset):
    paid = Payment.objects.filter(invoice_id=OuterRef("pk")).values("invoice_id").annotate(
        total=Sum("amount_paise"),
    ).values("total")[:1]
    return queryset.annotate(
        paid_paise=Coalesce(Subquery(paid), Value(0)),
    ).annotate(balance_paise=F("total_paise") - F("paid_paise"))


@role_required(*CUSTOMER_ROLE)
def index(request):
    today = timezone.localdate()
    subscriptions = _own_subscriptions(request.user)
    invoices = _own_invoices(request.user)
    outstanding_value = _with_invoice_balances(
        invoices.filter(status=Invoice.Status.CONFIRMED),
    ).aggregate(total=Sum("balance_paise"))["total"]
    recent_invoices = list(_with_invoice_balances(invoices)[:5])
    active_subscriptions = subscriptions.filter(
        status=Subscription.Status.ACTIVE,
        start_date__lte=today,
        expiry_date__gte=today,
    )
    active_subscriptions = active_subscriptions.exclude(
        is_paused=True, pause_effective_on__lte=today
    )
    return render(request, "portal/dashboard.html", {
        "active_count": active_subscriptions.count(),
        "subscription_count": subscriptions.count(),
        "invoice_count": invoices.count(),
        "outstanding_paise": outstanding_value or 0,
        "next_subscription": subscriptions.filter(
            status__in=[Subscription.Status.CONFIRMED, Subscription.Status.ACTIVE],
            next_invoice_date__isnull=False,
        ).order_by("next_invoice_date").first(),
        "recent_invoices": recent_invoices,
    })


@role_required(*CUSTOMER_ROLE)
def subscriptions(request):
    queryset = _own_subscriptions(request.user).prefetch_related("lines")
    page_obj = Paginator(queryset, 20).get_page(request.GET.get("page"))
    return render(request, "portal/subscription_list.html", {
        "page_obj": page_obj, "today": timezone.localdate(),
    })


@role_required(*CUSTOMER_ROLE)
def subscription_detail(request, subscription_id):
    subscription = get_object_or_404(
        _own_subscriptions(request.user).prefetch_related(
            "lines__product", "lines__variant", "successor"
        ),
        pk=subscription_id,
    )
    successor = getattr(subscription, "successor", None)
    return render(request, "portal/subscription_detail.html", {
        "subscription": subscription,
        "today": timezone.localdate(),
        "successor": successor,
        "renewal_requested": successor is not None,
        "can_request_renewal": (
            subscription.renewable_snapshot
            and successor is None
            and (subscription.status == Subscription.Status.CLOSED or subscription.expiry_date < timezone.localdate())
        ),
    })


@role_required(*CUSTOMER_ROLE)
def subscription_action(request, subscription_id, action_name):
    if request.method != "POST":
        raise PermissionDenied("Subscription actions require POST.")
    # Ownership is applied before lookup, so a foreign ID always resolves to
    # 404. Ignore any posted customer ID; lifecycle services validate actor.
    subscription = get_object_or_404(_own_subscriptions(request.user), pk=subscription_id)
    try:
        if action_name == "close":
            transition_subscription(
                subscription.pk, Subscription.Status.CLOSED, actor=request.user,
                reason=request.POST.get("reason", ""),
            )
            message = "Your subscription was closed."
        elif action_name == "pause":
            pause_subscription(subscription.pk, actor=request.user, reason=request.POST.get("reason", ""))
            message = "Your pause request was recorded."
        elif action_name == "resume":
            resume_subscription(subscription.pk, actor=request.user, reason=request.POST.get("reason", ""))
            message = "Your subscription was resumed."
        elif action_name == "renew":
            draft = renew_subscription(subscription.pk, actor=request.user)
            messages.success(request, f"Renewal requested. Draft {draft.number} is awaiting staff review.")
            return redirect("portal:subscription_detail", subscription.pk)
        else:
            raise PermissionDenied
    except DomainValidationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, message)
    return redirect("portal:subscription_detail", subscription.pk)


@role_required(*CUSTOMER_ROLE)
def invoices(request):
    page_obj = Paginator(_with_invoice_balances(_own_invoices(request.user)), 20).get_page(request.GET.get("page"))
    return render(request, "portal/invoice_list.html", {"page_obj": page_obj})


@role_required(*CUSTOMER_ROLE)
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(
        _own_invoices(request.user).prefetch_related("lines__tax_snapshots", "payments"),
        pk=invoice_id,
    )
    invoice.paid_paise = invoice.payments.aggregate(total=Sum("amount_paise"))["total"] or 0
    invoice.balance_paise = invoice.total_paise - invoice.paid_paise
    return render(request, "portal/invoice_detail.html", {"invoice": invoice})


@role_required(*CUSTOMER_ROLE)
def profile(request):
    # Profile editing is implemented by the shared customer profile endpoint;
    # keep a portal-owned entry point so customer navigation remains coherent.
    return redirect("customers:profile")
