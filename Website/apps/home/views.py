# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
from .models import Task, Holiday, Profile

import datetime as dt
import numpy as np

@login_required(login_url="/login/")
def index(request):
    logged_user = request.user
    hours_to_work = np.busday_count(logged_user.profile.contract_start_date, dt.date.today()) * logged_user.profile.hours_per_week/5 # TODO: add Feiertage
    tasks = Task.objects.filter(assigned_to=logged_user)
    worked_hours = sum([task.worked_hours for task in tasks])
    worked_hours_pct = round(worked_hours / hours_to_work * 100, 2) if worked_hours < hours_to_work else 100
    planned_hours = sum([task.total_hours for task in tasks])
    planned_hours_pct = round(planned_hours / hours_to_work * 100, 2) if planned_hours < hours_to_work else 100
    excess_hours = hours_to_work - worked_hours
    
    context = {
        'segment': 'index', 
        'hours_to_work': hours_to_work,  
        'worked_hours': worked_hours, 
        'worked_hours_pct': worked_hours_pct, 
        'planned_hours': planned_hours, 
        'planned_hours_pct': planned_hours_pct,
        'carry_over_hours_from_last_semester': logged_user.profile.carry_over_hours_from_last_semester,
        'excess_hours': excess_hours,
        'tasks': tasks
    }

    html_template = loader.get_template('home/index.html')
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
