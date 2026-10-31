from django.contrib.auth.base_user import BaseUserManager


def normalize_email_address(email):
    """Normalize the demo application's email identity (trimmed, lowercase)."""
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        email = normalize_email_address(email)
        if not email:
            raise ValueError("An email address is required.")

        # Django-admin access follows the business role. Callers cannot grant
        # staff/superuser access by passing the normal AbstractUser flags.
        extra_fields.pop("is_staff", None)
        extra_fields.pop("is_superuser", None)
        role = extra_fields.get("role", "CUSTOMER")
        extra_fields["is_staff"] = role == "ADMIN"
        extra_fields["is_superuser"] = False

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "CUSTOMER")
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["role"] = "ADMIN"
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        user = self._create_user(email, password, **extra_fields)
        user.is_superuser = True
        user.save(using=self._db, update_fields=["is_superuser"])
        return user

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD: normalize_email_address(username)})
