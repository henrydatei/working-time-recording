from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

import datetime as dt

# Create your models here.

class Task(models.Model):
    id = models.AutoField(primary_key=True)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE)
    assigner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigner')
    task_text = models.TextField()
    total_hours = models.FloatField()
    worked_hours = models.FloatField()
    deadline = models.DateField()

    def __str__(self):
        return self.task_text

    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['id']
        
class Holiday(models.Model):
    id = models.AutoField(primary_key=True)
    from_date = models.DateField()
    to_date = models.DateField()
    by_id = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.from_date) + " - " + str(self.to_date)

    class Meta:
        verbose_name = 'Holiday'
        verbose_name_plural = 'Holidays'
        ordering = ['id']
        
class Contract(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user', default=None, null=False, blank=True)
    contract_start_date = models.DateField(default=None, null=True, blank=True)
    contract_end_date = models.DateField(default=None, null=True, blank=True)
    hours_per_week = models.FloatField(default=0)
    carry_over_hours_from_last_semester = models.FloatField(default=0, help_text='Usually 0, in the contract overview you can let the number be calculated from the last semester. Only change if you know what you are doing.')
    carry_over_holiday_hours_from_last_semester = models.FloatField(default=0, help_text='Usually 0, in the contract overview you can let the number be calculated from the last semester. Only change if you know what you are doing.')
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervisor', default=None, null=True, blank=True)

    def __str__(self):
        return self.user.username + '\'s contract for ' + str(self.hours_per_week) + ' hours per week'

    class Meta:
        verbose_name = 'Contract'
        verbose_name_plural = 'Contracts'
        ordering = ['id']
        
class ContractChange(models.Model):
    id = models.AutoField(primary_key=True)
    contract_id = models.ForeignKey(Contract, on_delete=models.CASCADE)
    from_date = models.DateField()
    to_date = models.DateField(default=None, null=True, blank=True, help_text='Leave blank if you don\'t know when the contract change ends. Calculation will assume in this case that the contract change is till the end of the contract. If you add a second contract change, the end date of the first contract change will be set to the day before the start date of the second contract change.')
    hours_per_week = models.FloatField(default=0)
    
    def __str__(self):
        return 'Change ' + str(self.contract_id) + ' from ' + str(self.from_date) + ' to ' + str(self.to_date) + ' for ' + str(self.hours_per_week) + ' hours per week'

    class Meta:
        verbose_name = 'Contract Change'
        verbose_name_plural = 'Contract Changes'
        ordering = ['id']
        
    def save(self, *args, **kwargs):
        if not self.pk:
            # Check if there is a previous contract change
            previous_change = ContractChange.objects.filter(contract_id=self.contract_id).order_by('-from_date').first()
            
            if previous_change and not previous_change.to_date:
                # If there is a previous contract change and it doesn't have a to_date, set it to the from_date of the current contract change
                previous_change.to_date = self.from_date - dt.timedelta(days=1)
                previous_change._skip_save = True  # Flag, so that the save method doesn't get called again
                previous_change.save()

        super().save(*args, **kwargs)