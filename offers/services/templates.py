"""Copy quotation template terms into independent subscription rows."""

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import QuoteTemplate, Subscription, SubscriptionLine


def validate_quote_template(template):
    """Return an active, complete template or raise a useful validation error."""
    if not template or not template.is_active:
        raise ValidationError("Choose an active quotation template.")
    lines = list(template.lines.select_related("product", "variant").prefetch_related("taxes"))
    primary = [line for line in lines if line.is_primary]
    if len(primary) != 1:
        raise ValidationError("The template must contain exactly one primary line.")
    if primary[0].product_id != template.plan.primary_product_id:
        raise ValidationError("The primary template line must match the selected plan.")
    for line in lines:
        if line.quantity < (template.plan.min_quantity if line.is_primary else 1):
            raise ValidationError("A template line is below the required minimum quantity.")
        if not line.product.is_active or (line.variant and (not line.variant.is_active or line.variant.product_id != line.product_id)):
            raise ValidationError("The template contains an unavailable product or variant.")
        if line.unit_price_paise < 0:
            raise ValidationError("Template prices cannot be negative.")
    return lines


@transaction.atomic
def copy_template_to_subscription(template, subscription, *, replace=False):
    """Copy template line values and tax selections into subscription rows.

    The subscription retains the template as provenance only; invoices and
    contract prices use the copied line snapshots.
    """
    template = QuoteTemplate.objects.select_for_update().select_related("plan").get(pk=template.pk)
    subscription = Subscription.objects.select_for_update().get(pk=subscription.pk)
    if subscription.status != Subscription.Status.DRAFT:
        raise ValidationError("Templates can only be applied to a draft subscription.")
    if subscription.plan_id != template.plan_id:
        raise ValidationError("Choose a template for the subscription's selected plan.")
    lines = validate_quote_template(template)
    if replace:
        subscription.lines.all().delete()
    elif subscription.lines.exists():
        raise ValidationError("The draft already has lines; edit it or replace its lines explicitly.")
    for source in lines:
        copied = SubscriptionLine.objects.create(
            subscription=subscription,
            product=source.product,
            variant=source.variant,
            is_primary=source.is_primary,
            description=source.product.name,
            quantity=source.quantity,
            unit_price_paise=source.unit_price_paise,
            position=source.position,
        )
        copied.taxes.set(source.taxes.filter(is_active=True))
    subscription.source_template = template
    subscription.save(update_fields=["source_template", "updated_at"])
    return subscription
