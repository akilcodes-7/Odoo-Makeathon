from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from accounts.permissions import role_required
from core.models import Invoice, Payment
from core.services.exceptions import DomainValidationError
from core.services.finance import get_invoice_balance
from core.services.lifecycle import transition_invoice
from .services.payments import invoice_is_overdue


@role_required(User.Role.ADMIN, User.Role.STAFF)
def invoice_list(request):
    payment_totals = Payment.objects.filter(invoice_id=OuterRef("pk")).values("invoice_id").annotate(total=Sum("amount_paise")).values("total")[:1]
    invoices = Invoice.objects.select_related("subscription", "subscription__customer").annotate(
        paid_paise=Coalesce(Subquery(payment_totals), Value(0)),
    ).annotate(balance_paise=F("total_paise") - F("paid_paise"))
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        invoices = invoices.filter(Q(number__icontains=query) | Q(customer_name__icontains=query))
    if status in {value for value, _label in Invoice.Status.choices}:
        invoices = invoices.filter(status=status)
    page_obj = Paginator(invoices.order_by("-invoice_date", "-pk"), 25).get_page(request.GET.get("page"))
    from django.utils import timezone
    today = timezone.localdate()
    for invoice in page_obj:
        invoice.is_overdue = invoice.status == Invoice.Status.CONFIRMED and invoice.due_date < today and invoice.balance_paise > 0
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return render(request, "finance/invoice_list.html", {
        "page_obj": page_obj, "query": query, "status": status,
        "statuses": Invoice.Status.choices, "query_string": query_params.urlencode(),
    })


@role_required(User.Role.ADMIN, User.Role.STAFF)
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related("subscription", "subscription__customer")
        .prefetch_related("lines__tax_snapshots", "payments__created_by"),
        pk=invoice_id,
    )
    invoice.balance_paise = get_invoice_balance(invoice.pk)
    invoice.is_overdue = invoice_is_overdue(invoice.pk)
    return render(request, "finance/invoice_detail.html", {"invoice": invoice})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def invoice_action(request, invoice_id, action_name):
    if request.method != "POST":
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Invoice actions require POST.")
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    target = {"confirm": Invoice.Status.CONFIRMED, "cancel": Invoice.Status.CANCELLED}.get(action_name)
    if target is None:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    try:
        transition_invoice(invoice.pk, target, actor=request.user, reason=request.POST.get("reason", ""))
    except DomainValidationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"Invoice status is now {Invoice.objects.get(pk=invoice.pk).get_status_display()}.")
    return redirect("finance:invoice_detail", invoice.pk)


def index(request):
    return invoice_list(request)
