from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.permissions import role_required
from accounts.models import User
from core.models import Plan, Product, ProductVariant, Tax
from core.services.money import format_paise

from .forms import PlanForm, ProductForm, TaxForm, VariantForm


def _page(request, queryset):
    return Paginator(queryset, 25).get_page(request.GET.get("page"))


def _search(queryset, request, *fields):
    term = request.GET.get("q", "").strip()
    if term:
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": term})
        queryset = queryset.filter(query)
    return queryset


@role_required(User.Role.ADMIN, User.Role.STAFF, User.Role.CUSTOMER)
def index(request):
    if request.user.role == User.Role.CUSTOMER:
        return redirect("catalog:plans")
    return redirect("catalog:products")


@role_required(User.Role.ADMIN, User.Role.STAFF)
def products(request):
    rows = _search(Product.objects.filter(is_active=True).prefetch_related("variants"), request, "name", "notes")
    page_obj = _page(request, rows)
    for product in page_obj:
        product.sales_price_display = format_paise(product.sales_price_paise)
        product.cost_price_display = format_paise(product.cost_price_paise)
    return render(request, "catalog/product_list.html", {"page_obj": page_obj, "query": request.GET.get("q", "")})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related("variants", "plans"), pk=pk)
    product.sales_price_display = format_paise(product.sales_price_paise)
    product.cost_price_display = format_paise(product.cost_price_paise)
    for variant in product.variants.all():
        variant.extra_price_display = format_paise(variant.extra_price_paise)
    return render(request, "catalog/product_detail.html", {"product": product})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def variants(request):
    rows = ProductVariant.objects.filter(is_active=True, product__is_active=True).select_related("product")
    rows = _search(rows, request, "product__name", "attribute_name", "attribute_value")
    page_obj = _page(request, rows)
    for variant in page_obj:
        variant.extra_price_display = format_paise(variant.extra_price_paise)
    return render(request, "catalog/variant_list.html", {"page_obj": page_obj, "query": request.GET.get("q", "")})


@role_required(User.Role.ADMIN)
def product_create(request):
    return _edit(request, ProductForm(), "Product", "catalog:products")


@role_required(User.Role.ADMIN)
def product_edit(request, pk):
    return _edit(request, ProductForm(request.POST or None, instance=get_object_or_404(Product, pk=pk)), "Product", "catalog:product_detail", pk=pk)


@role_required(User.Role.ADMIN)
@require_POST
def product_archive(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False
    product.save(update_fields=["is_active", "updated_at"])
    messages.success(request, "Product archived. Existing records remain available.")
    return redirect("catalog:products")


@role_required(User.Role.ADMIN)
def variant_create(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk, is_active=True)
    form = VariantForm(request.POST or None, initial={"product": product})
    form.fields["product"].queryset = Product.objects.filter(pk=product.pk, is_active=True)
    if request.method == "POST":
        response = _save_form(request, form, "catalog:product_detail", pk=product.pk, success="Variant saved.")
        if response:
            return response
    return render(request, "catalog/form.html", {"form": form, "title": "Add product variant", "cancel_url": reverse("catalog:product_detail", args=[product.pk])})


@role_required(User.Role.ADMIN)
def variant_edit(request, pk):
    variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=pk)
    form = VariantForm(request.POST or None, instance=variant)
    if request.method == "POST":
        response = _save_form(request, form, "catalog:product_detail", pk=variant.product_id, success="Variant updated.")
        if response:
            return response
    return render(request, "catalog/form.html", {"form": form, "title": "Edit variant", "cancel_url": reverse("catalog:product_detail", args=[variant.product_id])})


@role_required(User.Role.ADMIN)
@require_POST
def variant_archive(request, pk):
    variant = get_object_or_404(ProductVariant, pk=pk)
    variant.is_active = False
    variant.save(update_fields=["is_active", "updated_at"])
    messages.success(request, "Variant archived.")
    return redirect("catalog:product_detail", pk=variant.product_id)


@role_required(User.Role.ADMIN, User.Role.STAFF, User.Role.CUSTOMER)
def plans(request):
    rows = Plan.objects.select_related("primary_product")
    if request.user.role == User.Role.CUSTOMER:
        today = timezone.localdate()
        rows = rows.filter(is_active=True, primary_product__is_active=True, available_from__lte=today).filter(
            Q(available_until__isnull=True) | Q(available_until__gte=today)
        )
    else:
        rows = rows.filter(is_active=True, primary_product__is_active=True)
    rows = _search(rows, request, "name", "primary_product__name")
    page_obj = _page(request, rows)
    for plan in page_obj:
        plan.price_display = format_paise(plan.price_paise)
    return render(request, "catalog/plan_list.html", {"page_obj": page_obj, "query": request.GET.get("q", ""), "customer_view": request.user.role == User.Role.CUSTOMER})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def plan_detail(request, pk):
    plan = get_object_or_404(Plan.objects.select_related("primary_product"), pk=pk)
    plan.price_display = format_paise(plan.price_paise)
    return render(request, "catalog/plan_detail.html", {"plan": plan})


@role_required(User.Role.ADMIN)
def plan_create(request):
    return _edit(request, PlanForm(request.POST or None), "Plan", "catalog:plans")


@role_required(User.Role.ADMIN)
def plan_edit(request, pk):
    return _edit(request, PlanForm(request.POST or None, instance=get_object_or_404(Plan, pk=pk)), "Plan", "catalog:plan_detail", pk=pk)


@role_required(User.Role.ADMIN)
@require_POST
def plan_archive(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    plan.is_active = False
    plan.save(update_fields=["is_active", "updated_at"])
    messages.success(request, "Plan archived. Existing contracts remain unchanged.")
    return redirect("catalog:plans")


@role_required(User.Role.ADMIN, User.Role.STAFF)
def taxes(request):
    rows = _search(Tax.objects.filter(is_active=True), request, "name")
    page_obj = _page(request, rows)
    for tax in page_obj:
        tax.percent_display = f"{tax.rate_bps // 100}.{tax.rate_bps % 100:02d}%"
    return render(request, "catalog/tax_list.html", {"page_obj": page_obj, "query": request.GET.get("q", "")})


@role_required(User.Role.ADMIN)
def tax_create(request):
    return _edit(request, TaxForm(request.POST or None), "Tax", "catalog:taxes")


@role_required(User.Role.ADMIN)
def tax_edit(request, pk):
    return _edit(request, TaxForm(request.POST or None, instance=get_object_or_404(Tax, pk=pk)), "Tax", "catalog:taxes")


@role_required(User.Role.ADMIN)
@require_POST
def tax_archive(request, pk):
    tax = get_object_or_404(Tax, pk=pk)
    tax.is_active = False
    tax.save(update_fields=["is_active", "updated_at"])
    messages.success(request, "Tax archived. Saved invoice tax snapshots are unchanged.")
    return redirect("catalog:taxes")


def _edit(request, form, title, success_url, **url_kwargs):
    if request.method == "POST":
        response = _save_form(request, form, success_url, success=title + " saved.", **url_kwargs)
        if response:
            return response
    return render(request, "catalog/form.html", {"form": form, "title": "Edit " + title.lower() if form.instance.pk else "New " + title.lower(), "cancel_url": reverse(success_url, kwargs=url_kwargs)})


def _save_form(request, form, success_url, success, **url_kwargs):
    if form.is_valid():
        if hasattr(form.instance, "created_by_id") and not form.instance.pk:
            form.instance.created_by = request.user
        try:
            instance = form.save()
        except (IntegrityError, ValidationError):
            form.add_error(None, "This record conflicts with existing catalog data. Check the values and try again.")
            return
        messages.success(request, success)
        return redirect(success_url, **url_kwargs)
