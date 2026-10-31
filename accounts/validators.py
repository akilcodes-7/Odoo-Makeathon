from django.core.exceptions import ValidationError


def validate_brightloop_password(password):
    """Enforce the password rule stated in the Brightloop build spec."""
    if len(password) < 9:
        raise ValidationError("Use at least 9 characters.", code="password_too_short")
    if not any(char.isupper() for char in password):
        raise ValidationError("Include at least one uppercase letter.", code="password_no_upper")
    if not any(char.islower() for char in password):
        raise ValidationError("Include at least one lowercase letter.", code="password_no_lower")
    if not any(not char.isalnum() and not char.isspace() for char in password):
        raise ValidationError("Include at least one special character.", code="password_no_special")
    if not password.strip():
        raise ValidationError("Password cannot contain only whitespace.", code="password_whitespace")
