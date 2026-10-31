from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone

from accounts.models import User
from accounts.permissions import role_required
from core.services.billing import run_due_billing


@role_required(User.Role.ADMIN, User.Role.STAFF)
def billing_index(request):
    return redirect("finance:invoices")


@role_required(User.Role.ADMIN, User.Role.STAFF)
def run_billing_view(request):
    if request.method != "POST":
        raise PermissionDenied("Billing runs require POST.")
    result = run_due_billing(as_of=timezone.localdate(), max_periods_per_subscription=3, actor=request.user)
    messages.success(request, f"Billing run created {len(result.created_ids)} invoices; {len(result.existing_ids)} already existed.")
    for error in result.errors:
        messages.error(request, error)
    if result.remaining_due_count:
        messages.warning(request, f"{result.remaining_due_count} periods remain due. Run billing again to continue the backlog.")
    return redirect("finance:invoices")
