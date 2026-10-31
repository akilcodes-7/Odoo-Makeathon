from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager, normalize_email_address


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STAFF = "STAFF", "Staff"
        CUSTOMER = "CUSTOMER", "Customer"

    username = None
    # Django's stock auth system requires the USERNAME_FIELD to be marked
    # unique. The Lower(email) constraint below supplies case-insensitive
    # uniqueness as well.
    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_uniq"),
        ]

    def save(self, *args, **kwargs):
        self.email = normalize_email_address(self.email)
        self.is_staff = self.role == self.Role.ADMIN
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.is_superuser = False
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"email", "is_staff", "is_superuser"}
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
