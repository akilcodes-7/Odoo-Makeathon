from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.permissions import role_required
from accounts.models import User
from core.models import Discount
from core.services.money import format_paise

from .forms import DiscountForm


def _decorate(discount):
    if discount.kind == Discount.Kind.FIXED:
        discount.value_display = format_paise(discount.amount_paise or 0)
    else:
        value = discount.percent_bps or 0
        discount.value_display = f"{value // 100}.{value % 100:02d}%"
    discount.minimum_display = format_paise(discount.min_purchase_paise)
    discount.remaining_uses = None if discount.max_uses is None else max(discount.max_uses - discount.used_count, 0)
    return discount


@role_required(User.Role.ADMIN)
def index(request):
    return redirect("offers:discounts")


@role_required(User.Role.ADMIN)
def discounts(request):
    rows = Discount.objects.prefetch_related("products").all()
    term = request.GET.get("q", "").strip()
    if term:
        rows = rows.filter(Q(name__icontains=term) | Q(products__name__icontains=term)).distinct()
    status = request.GET.get("status", "")
    if status == "active":
        rows = rows.filter(is_active=True)
    elif status == "archived":
        rows = rows.filter(is_active=False)
    page_obj = Paginator(rows, 25).get_page(request.GET.get("page"))
    for item in page_obj:
        _decorate(item)
    return render(request, "offers/discount_list.html", {"page_obj": page_obj, "query": term, "status": status})


@role_required(User.Role.ADMIN)
def discount_detail(request, pk):
    discount = get_object_or_404(Discount.objects.prefetch_related("products"), pk=pk)
    _decorate(discount)
    redemptions = discount.redemptions.select_related("invoice").order_by("-created_at", "-pk")[:25]
    for redemption in redemptions:
        if redemption.kind == Discount.Kind.FIXED:
            redemption.value_display = format_paise(redemption.value_paise or 0)
        else:
            value = redemption.value_bps or 0
            redemption.value_display = f"{value // 100}.{value % 100:02d}%"
        redemption.total_display = format_paise(redemption.total_discount_paise)
    return render(request, "offers/discount_detail.html", {"discount": discount, "redemptions": redemptions})


@role_required(User.Role.ADMIN)
def discount_create(request):
    return _edit(request, DiscountForm(request.POST or None), title="New discount", instance=None)


@role_required(User.Role.ADMIN)
def discount_edit(request, pk):
    instance = get_object_or_404(Discount, pk=pk)
    return _edit(request, DiscountForm(request.POST or None, instance=instance), title="Edit discount", instance=instance)


@role_required(User.Role.ADMIN)
@require_POST
def discount_archive(request, pk):
    discount = get_object_or_404(Discount, pk=pk)
    if discount.is_active:
        discount.is_active = False
        discount.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Discount archived. Existing invoice snapshots are unchanged.")
    return redirect("offers:discount_detail", pk=pk)


def _edit(request, form, *, title, instance):
    if request.method == "POST" and form.is_valid():
        capacity_conflict = False
        try:
            with transaction.atomic():
                if instance:
                    current = Discount.objects.select_for_update().get(pk=instance.pk)
                    # The edit form excludes the counter, so never write a stale
                    # usage count over a reservation committed while the form
                    # was open.
                    form.instance.used_count = current.used_count
                    new_limit = form.cleaned_data.get("max_uses")
                    if new_limit is not None and new_limit < current.used_count:
                        form.add_error("max_uses", "Maximum uses cannot be lower than the number already redeemed.")
                        capacity_conflict = True
                if not capacity_conflict:
                    discount = form.save(commit=False)
                    if discount._state.adding:
                        discount.created_by = request.user
                    discount.save()
                    form.save_m2m()
        except IntegrityError:
            form.add_error(None, "The discount conflicts with its usage limit or another database rule. Review the values and try again.")
        else:
            if not capacity_conflict:
                messages.success(request, "Discount saved.")
                return redirect("offers:discount_detail", pk=discount.pk)
    cancel_url = reverse("offers:discount_detail", args=[instance.pk]) if instance else reverse("offers:discounts")
    return render(request, "offers/discount_form.html", {"form": form, "title": title, "cancel_url": cancel_url, "instance": instance})
