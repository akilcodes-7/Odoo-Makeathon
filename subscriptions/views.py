from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from accounts.permissions import role_required
from core.models import QuoteTemplate, Subscription
from core.services.exceptions import DomainValidationError
from core.services.lifecycle import (
    pause_subscription, renew_subscription, resume_subscription,
    transition_subscription,
)
from offers.services.templates import copy_template_to_subscription, validate_quote_template
from .forms import DraftSubscriptionForm, SubscriptionLineFormSet


@role_required(User.Role.ADMIN, User.Role.STAFF)
def index(request):
    subscriptions = Subscription.objects.select_related("customer", "plan")
    query = request.GET.get("q", "").strip()
    if query:
        subscriptions = subscriptions.filter(Q(number__icontains=query) | Q(customer__display_name__icontains=query))
    status = request.GET.get("status", "")
    if status in {value for value, _label in Subscription.Status.choices}:
        subscriptions = subscriptions.filter(status=status)
    page_obj = Paginator(subscriptions.order_by("-created_at", "-pk"), 25).get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return render(request, "subscriptions/list.html", {"page_obj": page_obj, "query": query, "status": status, "statuses": Subscription.Status.choices, "query_string": query_params.urlencode(), "today": timezone.localdate()})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def create(request):
    form = DraftSubscriptionForm(request.POST or None)
    plan_id = request.POST.get("plan") if request.method == "POST" else request.GET.get("plan")
    plan = form.fields["plan"].queryset.filter(pk=plan_id).first() if plan_id else None
    formset = SubscriptionLineFormSet(request.POST or None, instance=Subscription(), plan=plan)
    valid_form = form.is_valid() if request.method == "POST" else False
    template = form.cleaned_data.get("quote_template") if valid_form else None
    valid_lines = True if template else formset.is_valid()
    if request.method == "POST" and valid_form and valid_lines:
        try:
            with transaction.atomic():
                if template:
                    validate_quote_template(template)
                subscription = form.save(commit=False)
                subscription.number = "SUB-TEMP"
                subscription.billing_period = subscription.plan.period
                subscription.billing_anchor_date = subscription.start_date
                subscription.created_by = request.user
                subscription.save()
                subscription.number = f"SUB-{subscription.pk:06d}"
                subscription.save(update_fields=["number", "updated_at"])
                if template:
                    copy_template_to_subscription(template, subscription)
                else:
                    formset.instance = subscription
                    formset.save()
        except (DomainValidationError, ValidationError, ValueError, IntegrityError) as exc:
            # Preserve a useful field-level validation for template mismatches
            # and database-integrity errors without leaving a partial draft.
            form.add_error("quote_template" if template else None, str(exc))
        else:
            messages.success(request, "Draft saved. Review the terms, then issue the quotation.")
            return redirect("subscriptions:detail", subscription.pk)
    return render(request, "subscriptions/form.html", {"form": form, "formset": formset, "page_title": "New draft"})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def detail(request, subscription_id):
    subscription = get_object_or_404(
        Subscription.objects.select_related("customer", "plan").prefetch_related("lines__product", "lines__variant", "lines__taxes", "events"),
        pk=subscription_id,
    )
    return render(request, "subscriptions/detail.html", {"subscription": subscription, "today": timezone.localdate()})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def edit(request, subscription_id):
    subscription = get_object_or_404(Subscription.objects.select_related("plan"), pk=subscription_id)
    if subscription.status != Subscription.Status.DRAFT:
        messages.error(request, "Confirmed contract terms are locked. Create a renewal draft to change them.")
        return redirect("subscriptions:detail", subscription.pk)
    form = DraftSubscriptionForm(request.POST or None, instance=subscription)
    plan = form.fields["plan"].queryset.filter(pk=request.POST.get("plan")).first() if request.method == "POST" else subscription.plan
    formset = SubscriptionLineFormSet(request.POST or None, instance=subscription, plan=plan)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            form.save()
            formset.save()
        messages.success(request, "Draft updated. Issue the quotation when the terms are ready.")
        return redirect("subscriptions:detail", subscription.pk)
    return render(request, "subscriptions/form.html", {"form": form, "formset": formset, "subscription": subscription, "page_title": "Edit draft"})


@role_required(User.Role.ADMIN, User.Role.STAFF)
def action(request, subscription_id, action_name):
    if request.method != "POST":
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Lifecycle actions require POST.")
    subscription = get_object_or_404(Subscription, pk=subscription_id)
    try:
        if action_name == "quote":
            if subscription.source_template_id:
                template = QuoteTemplate.objects.filter(pk=subscription.source_template_id).first()
                if template:
                    from datetime import timedelta
                    subscription.quote_expires_on = timezone.localdate() + timedelta(days=template.validity_days)
                    subscription.save(update_fields=["quote_expires_on", "updated_at"])
            result = transition_subscription(subscription.pk, Subscription.Status.QUOTATION, actor=request.user)
        elif action_name == "confirm":
            result = transition_subscription(subscription.pk, Subscription.Status.CONFIRMED, actor=request.user)
        elif action_name == "activate":
            result = transition_subscription(subscription.pk, Subscription.Status.ACTIVE, actor=request.user)
        elif action_name == "pause":
            result = pause_subscription(subscription.pk, actor=request.user, reason=request.POST.get("reason", ""))
        elif action_name == "resume":
            result = resume_subscription(subscription.pk, actor=request.user, reason=request.POST.get("reason", ""))
        elif action_name == "close":
            result = transition_subscription(subscription.pk, Subscription.Status.CLOSED, actor=request.user, reason=request.POST.get("reason", ""))
        elif action_name == "renew":
            result = renew_subscription(subscription.pk, actor=request.user)
            messages.info(request, f"Renewal requested as draft {result.number}.")
            return redirect("subscriptions:detail", result.pk)
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
    except DomainValidationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"Subscription status is now {result.get_status_display()}.")
    return redirect("subscriptions:detail", subscription.pk)
