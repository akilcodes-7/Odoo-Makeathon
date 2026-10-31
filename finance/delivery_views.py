from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.permissions import customer_owned, role_required
from core.models import Invoice
from core.services.exceptions import DomainValidationError
from core.services.finance import get_invoice_balance
from .services.delivery import delivery_mode, send_invoice
from .services.payments import invoice_is_overdue


STAFF_ROLES = (User.Role.ADMIN, User.Role.STAFF)


def _visible_invoice(request, invoice_id):
    if request.user.role in STAFF_ROLES:
        queryset = Invoice.objects.all()
    elif request.user.role == User.Role.CUSTOMER:
        queryset = customer_owned(Invoice.objects.all(), request.user, customer_path="subscription__customer")
        queryset = queryset.filter(status__in=[Invoice.Status.CONFIRMED, Invoice.Status.PAID])
    else:
        raise PermissionDenied
    return get_object_or_404(
        queryset.select_related("subscription", "subscription__customer")
        .select_related("discount_redemption")
        .prefetch_related("lines__tax_snapshots", "payments__created_by"),
        pk=invoice_id,
    )


@role_required(*STAFF_ROLES)
def invoice_send(request, invoice_id):
    if request.method != "POST":
        raise PermissionDenied("Invoice sending requires POST.")
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    try:
        send_invoice(
            invoice.pk,
            invoice_url=request.build_absolute_uri(reverse("finance_delivery:print", args=[invoice.pk])),
            actor=request.user,
        )
    except DomainValidationError as exc:
        messages.error(request, exc.message)
    except Exception:
        # Backend failures must be visible to the operator, and must not be
        # mistaken for a successful handoff.
        messages.error(request, "Email could not be handed to the configured backend. Invoice totals and status were not changed.")
    else:
        mode = delivery_mode()
        if mode == "smtp":
            messages.success(request, "Email handed to the mail server; inbox delivery is not confirmed.")
        elif mode == "local":
            messages.success(request, "Email written to local output; it was not delivered to the customer.")
        else:
            messages.success(request, "Email accepted by the configured backend; inbox delivery is not confirmed.")
    return redirect("finance:invoice_detail", invoice.pk)


def invoice_print(request, invoice_id):
    if not request.user.is_authenticated:
        from django.contrib.auth.views import redirect_to_login

        return redirect_to_login(request.get_full_path())
    invoice = _visible_invoice(request, invoice_id)
    if invoice.status not in {Invoice.Status.CONFIRMED, Invoice.Status.PAID}:
        raise PermissionDenied("Only confirmed or paid invoices can be printed.")
    invoice.balance_paise = get_invoice_balance(invoice.pk)
    invoice.paid_paise = invoice.payments.aggregate(total=Sum("amount_paise"))["total"] or 0
    invoice.is_overdue = invoice_is_overdue(invoice.pk, as_of=timezone.localdate())
    return render(request, "finance/invoice_print.html", {
        "invoice": invoice,
        "customer_view": request.user.role == User.Role.CUSTOMER,
    })
