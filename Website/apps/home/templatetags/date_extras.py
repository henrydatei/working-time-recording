from django import template
from numpy import busday_count

from ..views import get_free_days

register = template.Library()

@register.filter
def busdays(value, arg):
    """Counts the number of business days between two dates."""
    free_days = get_free_days(value, arg)
    return busday_count(value, arg) + 1 - len(free_days.keys())