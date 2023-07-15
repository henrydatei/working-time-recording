from django import template
from django.contrib.auth.models import Group, User

register = template.Library()

@register.filter(name='has_group') 
def has_group(user: User, group_name: str):
    group =  Group.objects.get(name=group_name) 
    return group in user.groups.all() 