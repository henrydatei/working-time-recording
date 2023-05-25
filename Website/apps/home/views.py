# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from django.shortcuts import get_object_or_404

from .models import Task, Holiday, Profile
from django.contrib.auth.models import User
from django.db.models import F

import datetime as dt
import numpy as np

@login_required(login_url="/login/")
def index(request):
    logged_user = request.user
    
    # process form
    if request.method == 'POST':
        if request.POST["formType"] == "newTask":
            t = Task(assigned_to = logged_user, assigner = User.objects.get(id=request.POST["taskGivenBy"]), task_text = request.POST["TaskDescription"], total_hours = request.POST["plannedHours"], worked_hours = request.POST["workedHours"], deadline = request.POST["deadline"])
            if t.worked_hours <= t.total_hours:
                t.save()
        elif request.POST["formType"] == "updateTask":
            t = Task.objects.get(id=request.POST["taskId"])
            t.worked_hours = request.POST["actualHours"]
            t.total_hours = request.POST["plannedHours"]
            if t.worked_hours <= t.total_hours:
                t.save()
    
    hours_to_work = np.busday_count(logged_user.profile.contract_start_date, dt.date.today()) * logged_user.profile.hours_per_week/5 # TODO: add Feiertage
    tasks = Task.objects.filter(assigned_to=logged_user)
    unfinished_tasks = Task.objects.filter(assigned_to=logged_user, worked_hours__lt = F('total_hours'))
    worked_hours = sum([task.worked_hours for task in tasks])
    worked_hours_pct = round(worked_hours / hours_to_work * 100, 2) if worked_hours < hours_to_work else 100
    planned_hours = sum([task.total_hours for task in tasks])
    planned_hours_pct = round(planned_hours / hours_to_work * 100, 2) if planned_hours < hours_to_work else 100
    excess_hours = hours_to_work - worked_hours
    
    # all users in group supervisor
    supervisors = User.objects.filter(groups__name='supervisor')
    
    context = {
        'segment': 'index', 
        'hours_to_work': hours_to_work,  
        'worked_hours': worked_hours, 
        'worked_hours_pct': worked_hours_pct, 
        'planned_hours': planned_hours, 
        'planned_hours_pct': planned_hours_pct,
        'carry_over_hours_from_last_semester': logged_user.profile.carry_over_hours_from_last_semester,
        'excess_hours': excess_hours,
        'tasks': unfinished_tasks,
        'supervisors': supervisors,
        'my_supervisor': logged_user.profile.supervisor,
    }

    html_template = loader.get_template('home/index.html')
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def tasks(request):
    logged_user = request.user
    
    # process Form
    if request.method == 'POST':
        t = Task.objects.get(id=request.POST["taskId"])
        t.task_text = request.POST["taskDescription"]
        t.total_hours = request.POST["plannedHours"]
        t.worked_hours = request.POST["workedHours"]
        t.deadline = request.POST["deadline"]
        t.assigner = User.objects.get(id=request.POST["taskGivenBy"])
        t.save()
    
    tasks = Task.objects.filter(assigned_to=logged_user)
    
    context = {
        'segment': 'tasks',
        'tasks': tasks,
    }
    
    html_template = loader.get_template('home/tasks.html')
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def editTask(request, task_id):
    logged_user = request.user
    task = get_object_or_404(Task, pk=task_id, assigned_to=logged_user)
    supervisors = User.objects.filter(groups__name='supervisor')
    
    context = {
        'segment': 'editTask',
        'task': task,
        'supervisors': supervisors,
    }
    
    html_template = loader.get_template('home/editTask.html')
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def holidays(request):
    context = {}
    logged_user = request.user
    
    html_template = loader.get_template('home/holidays.html')
    return HttpResponse(html_template.render(context, request))


@login_required(login_url="/login/")
def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:

        load_template = request.path.split('/')[-1]

        if load_template == 'admin':
            return HttpResponseRedirect(reverse('admin:index'))
        context['segment'] = load_template

        html_template = loader.get_template('home/' + load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:

        html_template = loader.get_template('home/page-404.html')
        return HttpResponse(html_template.render(context, request))

    except:
        html_template = loader.get_template('home/page-500.html')
        return HttpResponse(html_template.render(context, request))
