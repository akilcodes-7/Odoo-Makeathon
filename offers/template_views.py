from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from accounts.permissions import role_required
from core.models import QuoteTemplate
from .services.templates import validate_quote_template
from .template_forms import QuoteTemplateForm, QuoteTemplateLineFormSet


@role_required(User.Role.ADMIN, User.Role.STAFF)
def index(request):
    rows = QuoteTemplate.objects.select_related("plan", "plan__primary_product").prefetch_related("lines").order_by("name", "pk")
    page_obj = Paginator(rows, 25).get_page(request.GET.get("page"))
    return render(request, "offers/template_list.html", {"page_obj": page_obj})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def detail(request, template_id):
    template = get_object_or_404(QuoteTemplate.objects.select_related("plan", "plan__primary_product").prefetch_related("lines__product", "lines__variant", "lines__taxes"), pk=template_id)
    return render(request, "offers/template_detail.html", {"template": template})


@role_required(User.Role.ADMIN)
def create(request):
    form = QuoteTemplateForm(request.POST or None)
    template = QuoteTemplate()
    if form.is_bound and form.is_valid():
        template = form.save(commit=False)
        template.created_by = request.user
    formset = QuoteTemplateLineFormSet(request.POST or None, instance=template)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            formset.instance = template
            formset.save()
        try:
            validate_quote_template(template)
        except ValidationError as exc:
            # Keep invalid templates inactive; the list explains the validation
            # issue before a staff member can select one.
            template.is_active = False
            template.save(update_fields=["is_active", "updated_at"])
            messages.warning(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Quotation template saved.")
        return redirect("offers:template_detail", template.pk)
    return render(request, "offers/template_form.html", {"form": form, "formset": formset, "page_title": "New quotation template"})


@role_required(User.Role.ADMIN)
def edit(request, template_id):
    template = get_object_or_404(QuoteTemplate.objects.prefetch_related("lines__taxes"), pk=template_id)
    form = QuoteTemplateForm(request.POST or None, instance=template)
    formset = QuoteTemplateLineFormSet(request.POST or None, instance=template)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            form.save()
            formset.save()
        try:
            validate_quote_template(template)
        except ValidationError as exc:
            messages.warning(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Quotation template updated.")
        return redirect("offers:template_detail", template.pk)
    return render(request, "offers/template_form.html", {"form": form, "formset": formset, "template": template, "page_title": "Edit quotation template"})
