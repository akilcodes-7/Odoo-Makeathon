"""Email handoff for immutable invoice snapshots."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.html import escape

from core.models import Invoice
from core.services.exceptions import DomainValidationError


def send_invoice(invoice_id, *, invoice_url, actor):
    """Send a confirmed/paid invoice to its snapshotted billing address.

    ``sent_at`` records successful backend handoff only. A backend error is
    propagated without touching invoice state or financial values.
    """
    invoice = Invoice.objects.get(pk=invoice_id)
    if getattr(actor, "role", None) not in {"ADMIN", "STAFF"}:
        raise DomainValidationError("forbidden", "Only finance staff can send invoices.")
    if invoice.status not in {Invoice.Status.CONFIRMED, Invoice.Status.PAID}:
        raise DomainValidationError("invoice_not_sendable", "Only confirmed or paid invoices can be sent.")
    recipient = (invoice.customer_email or "").strip()
    try:
        validate_email(recipient)
    except ValidationError:
        raise DomainValidationError("invalid_snapshot_email", "The invoice has no valid billing email in its saved snapshot.")

    subject = f"Invoice {invoice.number} from Brightloop"
    plain = (
        f"Hello {invoice.customer_name},\n\n"
        f"Invoice {invoice.number} is ready. Total: {invoice.currency} "
        f"{invoice.total_paise // 100}.{invoice.total_paise % 100:02d}.\n"
        f"View or print the invoice after signing in: {invoice_url}\n"
    )
    html = (
        f"<p>Hello {escape(invoice.customer_name)},</p>"
        f"<p>Invoice <strong>{escape(invoice.number)}</strong> is ready. "
        f"Total: {escape(invoice.currency)} {invoice.total_paise // 100}.{invoice.total_paise % 100:02d}.</p>"
        f'<p><a href="{escape(invoice_url)}">Sign in to view or print your invoice</a></p>'
    )
    message = EmailMultiAlternatives(subject, plain, settings.DEFAULT_FROM_EMAIL, [recipient])
    message.attach_alternative(html, "text/html")
    # Send before recording the timestamp; a raised exception leaves the invoice untouched.
    sent = message.send(fail_silently=False)
    if not sent:
        raise DomainValidationError("email_not_accepted", "The configured email backend did not accept the message.")

    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(pk=invoice_id)
        locked.sent_at = timezone.now()
        locked.save(update_fields=["sent_at", "updated_at"])
    return locked


def delivery_mode():
    backend = settings.EMAIL_BACKEND
    if backend == "django.core.mail.backends.smtp.EmailBackend":
        return "smtp"
    if backend in {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
    }:
        return "local"
    return "configured"
