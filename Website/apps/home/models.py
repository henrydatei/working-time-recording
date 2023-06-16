from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    carry_over_hours_from_last_semester = models.FloatField(default=0)
    carry_over_holiday_hours_from_last_semester = models.FloatField(default=0)
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervisor', default=None, null=True, blank=True)

    def __str__(self):
        return self.user.username + '\'s contract for ' + str(self.hours_per_week) + ' hours per week'

    class Meta:
        verbose_name = 'Contract'
        verbose_name_plural = 'Contracts'
        ordering = ['id']