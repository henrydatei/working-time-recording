from django import template

from ..views import get_free_days, business_days

register = template.Library()

@register.filter
def busdays(value, arg):
    """Counts the number of business days between two dates."""
    free_days = get_free_days(value, arg)
    return business_days(value, arg) - len(free_days.keys())