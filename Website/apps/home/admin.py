from django.contrib import admin
from .models import Task, Holiday, Contract, ContractChange

# Register your models here.
admin.site.register(Task)
admin.site.register(Holiday)
admin.site.register(Contract)
admin.site.register(ContractChange)