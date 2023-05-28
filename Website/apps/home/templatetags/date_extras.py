from django import template
from numpy import busday_count

register = template.Library()

@register.filter
def busdays(value, arg):
    """Counts the number of business days between two dates."""
    return busday_count(value, arg) + 1 # TODO: add Feiertage