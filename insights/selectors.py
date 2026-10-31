"""Role-scoped dashboard queries and financial summary calculations."""

from datetime import date
from decimal import Decimal

from django.db.models import BigIntegerField, Count, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from accounts.models import User
from accounts.permissions import customer_owned
from core.models import Customer, Invoice, Payment, Subscription, SubscriptionLine
from core.services.money import round_half_up


def customer_scope(user, *, requested_customer=""):
    """Return a customer id for CUSTOMER users, and validate staff filters."""
    if user.role == User.Role.CUSTOMER:
        return Customer.objects.filter(user=user).values_list("pk", flat=True).first()
    if not requested_customer:
        return None
    try:
        customer_id = int(requested_customer)
    except (TypeError, ValueError) as exc:
        raise ValueError("Choose a valid customer.") from exc
    if not Customer.objects.filter(pk=customer_id).exists():
        raise ValueError("Choose a valid customer.")
    return customer_id


def scoped_subscriptions(user, customer_id=None):
    qs = Subscription.objects.all()
    if user.role == User.Role.CUSTOMER:
        qs = customer_owned(qs, user)
    if customer_id is not None:
        qs = qs.filter(customer_id=customer_id)
    return qs


def scoped_invoices(user, customer_id=None):
    qs = Invoice.objects.all()
    if user.role == User.Role.CUSTOMER:
        qs = customer_owned(qs, user, customer_path="subscription__customer")
    if customer_id is not None:
        qs = qs.filter(subscription__customer_id=customer_id)
    return qs


def _paid_subquery():
    return Payment.objects.filter(invoice_id=OuterRef("pk")).values("invoice_id").annotate(
        paid=Sum("amount_paise")
    ).values("paid")[:1]


def invoices_with_balance(user, customer_id=None):
    """Annotate invoice balances from payment rows without joining other sums."""
    return scoped_invoices(user, customer_id).annotate(
        paid_paise=Coalesce(Subquery(_paid_subquery(), output_field=BigIntegerField()), Value(0), output_field=BigIntegerField()),
    ).annotate(balance_paise=F("total_paise") - F("paid_paise"))


def active_subscriptions(user, customer_id=None, *, as_of: date):
    return scoped_subscriptions(user, customer_id).filter(
        status=Subscription.Status.ACTIVE,
        start_date__lte=as_of,
        expiry_date__gte=as_of,
    ).filter(~Q(is_paused=True, pause_effective_on__lte=as_of))


def dashboard_summary(user, *, customer_id, start_date: date, end_date: date, as_of: date):
    """Build metrics from separate scoped querysets to prevent aggregate fan-out."""
    invoice_qs = scoped_invoices(user, customer_id)
    subscription_qs = scoped_subscriptions(user, customer_id)

    payment_qs = Payment.objects.filter(
        invoice__in=invoice_qs,
        paid_on__gte=start_date,
        paid_on__lte=end_date,
    )
    collected = payment_qs.aggregate(total=Sum("amount_paise"))["total"] or 0
    collection_days = list(payment_qs.values("paid_on").annotate(
        amount_paise=Sum("amount_paise"), payments=Count("pk")
    ).order_by("paid_on")[:31])

    balances = invoices_with_balance(user, customer_id).filter(status=Invoice.Status.CONFIRMED, balance_paise__gt=0)
    receivables = balances.aggregate(
        total=Sum("balance_paise"), count=Count("pk"),
    )
    overdue = balances.filter(due_date__lt=as_of)
    overdue_totals = overdue.aggregate(total=Sum("balance_paise"), count=Count("pk"))

    active = active_subscriptions(user, customer_id, as_of=as_of)
    active_count = active.aggregate(count=Count("pk"))["count"] or 0
    bases = SubscriptionLine.objects.filter(subscription__in=active).values(
        "subscription__billing_period"
    ).annotate(
        base_paise=Sum(ExpressionWrapper(F("unit_price_paise") * F("quantity"), output_field=BigIntegerField()))
    )
    normalized_mrr_paise = Decimal(0)
    for row in bases:
        amount = Decimal(row["base_paise"] or 0)
        period = row["subscription__billing_period"]
        if period == Subscription.Period.DAILY:
            amount *= Decimal(365) / Decimal(12)
        elif period == Subscription.Period.WEEKLY:
            amount *= Decimal(52) / Decimal(12)
        elif period == Subscription.Period.YEARLY:
            amount /= Decimal(12)
        normalized_mrr_paise += amount

    invoiced = invoice_qs.filter(
        status__in=(Invoice.Status.CONFIRMED, Invoice.Status.PAID),
        invoice_date__gte=start_date,
        invoice_date__lte=end_date,
    ).aggregate(total=Sum("total_paise"))["total"] or 0

    return {
        "currency": "INR",
        "as_of": as_of,
        "range_start": start_date,
        "range_end": end_date,
        "active_subscriptions": active_count,
        "mrr_before_discounts_paise": round_half_up(normalized_mrr_paise),
        "outstanding_paise": receivables["total"] or 0,
        "outstanding_invoice_count": receivables["count"] or 0,
        "overdue_paise": overdue_totals["total"] or 0,
        "overdue_invoice_count": overdue_totals["count"] or 0,
        "collected_paise": collected,
        "invoiced_paise": invoiced,
        "collection_days": collection_days,
    }


def overdue_invoices(user, customer_id=None, *, as_of: date):
    return invoices_with_balance(user, customer_id).filter(
        status=Invoice.Status.CONFIRMED,
        due_date__lt=as_of,
        balance_paise__gt=0,
    ).select_related("subscription", "subscription__customer")
