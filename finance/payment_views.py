from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.permissions import role_required
from core.models import Invoice, Payment
from core.services.exceptions import DomainValidationError
from core.services.finance import get_invoice_balance
from .forms import PaymentForm
from .services.payments import record_payment


STAFF_ROLES = ("ADMIN", "STAFF")


@role_required(*STAFF_ROLES)
def payment_list(request):
    page = Paginator(
        Payment.objects.select_related("invoice", "invoice__subscription", "created_by").all(), 25
    ).get_page(request.GET.get("page"))
    return render(request, "finance/payment_list.html", {"payments": page})


@role_required(*STAFF_ROLES)
def payment_new(request, invoice_id):
    invoice = get_object_or_404(Invoice.objects.select_related("subscription"), pk=invoice_id)
    balance = get_invoice_balance(invoice.pk)
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                payment = record_payment(
                    invoice.pk,
                    amount_paise=form.cleaned_data["amount"],
                    method=form.cleaned_data["method"],
                    paid_on=form.cleaned_data["paid_on"],
                    note=form.cleaned_data["note"],
                    idempotency_key=form.cleaned_data["idempotency_key"],
                    actor=request.user,
                )
            except DomainValidationError as exc:
                if exc.field_errors:
                    for field, error in exc.field_errors.items():
                        form.add_error("amount" if field == "amount_paise" else field, error)
                else:
                    form.add_error(None, exc.message)
            else:
                messages.success(request, f"Payment of ₹{payment.amount_paise // 100}.{payment.amount_paise % 100:02d} recorded for {invoice.number}.")
                return redirect("finance_payments:list")
    else:
        form = PaymentForm(initial={"paid_on": timezone.localdate(), "idempotency_key": PaymentForm.fresh_key()})
    return render(request, "finance/payment_form.html", {"invoice": invoice, "balance_paise": balance, "form": form})
