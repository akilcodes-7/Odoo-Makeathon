from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import customer_owned, role_required
from accounts.models import User
from core.customer_forms import CustomerForm, OwnCustomerProfileForm, create_customer
from core.models import Customer, Invoice


@role_required(User.Role.ADMIN, User.Role.STAFF)
def customers_index(request):
    customers = Customer.objects.order_by("display_name", "pk")
    query = request.GET.get("q", "").strip()
    if query:
        customers = customers.filter(Q(display_name__icontains=query) | Q(billing_email__icontains=query))
    page_obj = Paginator(customers, 25).get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return render(request, "core/customers/list.html", {
        "customers": page_obj, "page_obj": page_obj, "query": query,
        "query_string": query_params.urlencode(),
    })


@role_required(User.Role.ADMIN, User.Role.STAFF)
def customer_detail(request, customer_id):
    customer = get_object_or_404(Customer.objects.select_related("user"), pk=customer_id)
    subscriptions = customer.subscriptions.select_related("plan").order_by("-created_at", "-pk")[:10]
    invoice_rows = Invoice.objects.filter(subscription__customer=customer).order_by("-invoice_date", "-pk")[:10]
    return render(request, "core/customers/detail.html", {
        "customer": customer, "subscriptions": subscriptions, "invoices": invoice_rows,
    })


@role_required(User.Role.ADMIN, User.Role.STAFF)
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            customer = create_customer(form)
        except Exception as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Customer saved without linking a login account.")
            return redirect("customers:edit", customer.pk)
    return render(request, "core/customers/form.html", {"form": form, "page_title": "Add customer"})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def customer_edit(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Customer profile updated.")
        return redirect("customers:edit", customer.pk)
    return render(request, "core/customers/form.html", {"form": form, "customer": customer, "page_title": "Edit customer"})


@login_required
def customer_profile(request):
    if request.user.role != User.Role.CUSTOMER:
        raise PermissionDenied
    customer = get_object_or_404(customer_owned(Customer.objects.all(), request.user))
    form = OwnCustomerProfileForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your contact details were updated.")
        return redirect("customers:profile")
    return render(request, "core/customers/form.html", {"form": form, "customer": customer, "page_title": "Your profile", "own_profile": True})
