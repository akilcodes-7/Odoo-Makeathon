from django.conf import settings
from django.db import models

from .base import TimestampedModel


class Customer(TimestampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_profile",
    )
    display_name = models.CharField(max_length=200)
    billing_email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    billing_address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_name", "pk"]
        indexes = [models.Index(fields=["is_active", "display_name"], name="customer_active_name_idx")]

    def __str__(self):
        return self.display_name
