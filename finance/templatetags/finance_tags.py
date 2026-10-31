from django import template

from core.services.money import format_paise

register = template.Library()


@register.filter
def paise(value):
    try:
        return format_paise(int(value))
    except (TypeError, ValueError):
        return "—"
