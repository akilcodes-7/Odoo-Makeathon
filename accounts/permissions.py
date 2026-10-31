from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet


require_login = login_required


def role_required(*roles):
    """Require an authenticated user with one of the named business roles."""
    allowed = frozenset(roles)

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if getattr(request.user, "role", None) not in allowed:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def customer_owned(queryset: QuerySet, user, *, customer_path=None) -> QuerySet:
    """Restrict a customer-related queryset to the signed-in user's profile."""
    if customer_path is None:
        fields = {field.name for field in queryset.model._meta.get_fields()}
        customer_path = "" if "user" in fields else "customer"
    lookup = f"{customer_path}__user" if customer_path else "user"
    return queryset.filter(**{lookup: user})
