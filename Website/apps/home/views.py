# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.template import loader
from django.urls import reverse
from django.shortcuts import get_object_or_404

from .models import Task, Holiday, Contract
from django.contrib.auth.models import User
from django.db.models import F

import datetime as dt
import numpy as np
import holidays as hd

from typing import Tuple

def get_free_days(from_date: dt.date, to_date: dt.date) -> dict:
    all_holidays = hd.country_holidays("DE", subdiv = "SN", years = [y for y in range(from_date.year, to_date.year + 1)])
    free_days = {}
    for date, name in sorted(all_holidays.items()):
        if from_date <= date <= to_date:
            free_days[date] = name
            
    return free_days 

def calc_holiday(user: User) -> Tuple[float, float, int, float]:
    """This function calculates the holiday entitlement, the not taken holidays, the taken holidays and the remaining holidays for a given user. Since the holiday entitlement is calculated based on the contract duration, the function iterates over all contracts of the user. Important are the number of full months worked, for 12 months you get 20 days off.

    Args:
        user (User): The user for which the holiday entitlement should be calculated.

    Returns:
        Tuple[float, float, float, float]: holiday entitlement, not taken holidays in last semester, taken holidays days, remaining holidays in days
    """
    contracts = Contract.objects.filter(user=user)
    holiday_entitlement_sum, not_taken_holidays_sum = 0, 0
    for contract in contracts:
        contract_duration = dt.date(contract.contract_end_date.year, contract.contract_end_date.month, contract.contract_end_date.day) - dt.date(contract.contract_start_date.year, contract.contract_start_date.month, contract.contract_start_date.day)
        full_months = contract_duration.days // 30
        holiday_entitlement = round(full_months * 20 / 12,0)
        not_taken_holidays = contract.carry_over_holiday_hours_from_last_semester / contract.hours_per_week * 5
        holiday_entitlement_sum += holiday_entitlement
        not_taken_holidays_sum += not_taken_holidays
    
    taken_holidays = Holiday.objects.filter(by_id=user)
    taken_holidays_days = sum([np.busday_count(holiday.from_date, holiday.to_date) + 1 - len(get_free_days(holiday.from_date, holiday.to_date).keys()) for holiday in taken_holidays])
    remaining_holidays = holiday_entitlement_sum + not_taken_holidays_sum - taken_holidays_days
    
    return holiday_entitlement_sum, not_taken_holidays_sum, taken_holidays_days, remaining_holidays

def calc_days_to_work(contract: Contract) -> int:
    """This function calculates the number of days you should have worked until now. If the contract is over it will return the total number of ways worked in the whole contract.

    Args:
        contract (Contract): The contract for which the number of days to work should be calculated.

    Returns:
        int: number of days to work
    """
    days_to_work = np.busday_count(contract.contract_start_date, min(dt.date.today(), contract.contract_end_date)) + 1 # TODO: add Feiertage, add Holidays
    return days_to_work

def calc_working_time(user: User) -> Tuple[float, float, float, float]:
    """This function calculates the hours to work, the worked hours, the planned hours and the excess hours for a given user. It uses the contract start date and the contract end date. If the contract end date is in the future, the current date is used instead. We do this for all contracts of the user and sum up the hours.

    Args:
        user (User): The user for which the working time should be calculated.

    Returns:
        Tuple[float, float, float, float]: hours to work, worked hours, planned hours, excess hours
    """
    contracts = Contract.objects.filter(user=user)
    hours_to_work = 0
    for contract in contracts:
        hours_to_work += calc_days_to_work(contract) * contract.hours_per_week/5
    
    tasks = Task.objects.filter(assigned_to=user)
    worked_hours = sum([task.worked_hours for task in tasks])
    planned_hours = sum([task.total_hours for task in tasks])
    excess_hours = hours_to_work - worked_hours
    
    return hours_to_work, worked_hours, planned_hours, excess_hours

def is_supervisor(user: User) -> bool:
    """This function checks if a given user is a supervisor.

    Args:
        user (User): The user to check.

    Returns:
        bool: True if the user is a supervisor, False otherwise.
    """
    return user.groups.filter(name='supervisor').exists()

def is_shkofficer(user: User) -> bool:
    """This function checks if a given user is a shkofficer.

    Args:
        user (User): The user to check.

    Returns:
        bool: True if the user is a shkofficer, False otherwise.
    """
    return user.groups.filter(name='shkofficer').exists()

@login_required(login_url="/login/")
def index(request: HttpRequest):
    logged_user = request.user
    
    if is_supervisor(logged_user) or is_shkofficer(logged_user):
        # user is supervisor or shkofficer
        # process form only if supervisor
        if request.method == 'POST' and is_supervisor(logged_user):
            if request.POST["formType"] == "newTask":
                t = Task(assigner = logged_user, assigned_to = User.objects.get(id=request.POST["taskGivenTo"]), task_text = request.POST["TaskDescription"], total_hours = request.POST["plannedHours"], worked_hours = 0, deadline = request.POST["deadline"])
                t.save()
                    
        shks_data = []
        if is_supervisor(logged_user):
            # only get shks of supervisor
            shks = Contract.objects.filter(supervisor=logged_user)
        else:
            # get all shks
            # since a shk can have multiple contracts, we only get the first one
            shks = [Contract.objects.filter(user=user).first() for user in User.objects.filter(groups__name='shk')]
        
        for shk in shks:
            hours_to_work, worked_hours, planned_hours, excess_hours = calc_working_time(shk.user)
            worked_hours_pct = round(worked_hours / hours_to_work * 100, 2) if worked_hours < hours_to_work else 100
            planned_hours_pct = round(planned_hours / hours_to_work * 100, 2) if planned_hours < hours_to_work else 100
            shks_data.append({
                'contract': shk,
                'worked_hours': worked_hours,
                'worked_hours_pct': worked_hours_pct,
                'planned_hours': planned_hours,
                'planned_hours_pct': planned_hours_pct,
                'difference_hours_pct': round(planned_hours_pct - worked_hours_pct, 2),
                'hours_to_work': hours_to_work,
                'excess_hours': excess_hours,
                'carry_over_hours_from_last_semester': shk.carry_over_hours_from_last_semester,
            })
        tasks = Task.objects.filter(assigned_to__in=[shk.user for shk in shks]).order_by('-deadline')[:10]
        
        context = {
            'segment': 'index',
            'shks': shks,
            'tasks': tasks,
            'shks_data': shks_data,
        }
        
        if is_supervisor(logged_user):
            html_template = loader.get_template('home/index_supervisor.html')
        else:
            html_template = loader.get_template('home/index_officer.html')
    else:
        # user is shk
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
        
        # working time
        hours_to_work, worked_hours, planned_hours, excess_hours = calc_working_time(logged_user)
        worked_hours_pct = round(worked_hours / hours_to_work * 100, 2) if worked_hours < hours_to_work else 100
        planned_hours_pct = round(planned_hours / hours_to_work * 100, 2) if planned_hours < hours_to_work else 100
        unfinished_tasks = Task.objects.filter(assigned_to=logged_user, worked_hours__lt = F('total_hours')).order_by('-deadline')
        
        # all users in group supervisor
        supervisors = User.objects.filter(groups__name='supervisor')
        
        context = {
            'segment': 'index', 
            'hours_to_work': hours_to_work,  
            'worked_hours': worked_hours, 
            'worked_hours_pct': worked_hours_pct, 
            'planned_hours': planned_hours, 
            'planned_hours_pct': planned_hours_pct,
            'carry_over_hours_from_last_semester': sum([contract.carry_over_hours_from_last_semester for contract in Contract.objects.filter(user=logged_user)]),
            'excess_hours': excess_hours,
            'tasks': unfinished_tasks,
            'supervisors': supervisors,
            'my_supervisor': Contract.objects.filter(user=logged_user).first().supervisor
        }

        html_template = loader.get_template('home/index.html')
        
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def tasks(request: HttpRequest):
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
    
    if is_supervisor(logged_user):
        shks = Contract.objects.filter(supervisor=logged_user)
        tasks = Task.objects.filter(assigned_to__in=[shk.user for shk in shks]).order_by('-deadline')
    elif is_shkofficer(logged_user):
        tasks = Task.objects.all().order_by('-deadline')
    else:
        tasks = Task.objects.filter(assigned_to=logged_user).order_by('-deadline')
    
    context = {
        'segment': 'tasks',
        'tasks': tasks,
    }
    
    html_template = loader.get_template('home/tasks.html')
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def editTask(request: HttpRequest, task_id: int):
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
def holidays(request: HttpRequest):
    logged_user = request.user
    
    if is_supervisor(logged_user) or is_shkofficer(logged_user):
        shks_data = []
        if is_supervisor(logged_user):
            # only get shks of supervisor
            shks = Contract.objects.filter(supervisor=logged_user)
        else:
            # get all shks
            # since a shk can have multiple contracts, we only get the first one
            shks = [Contract.objects.filter(user=user).first() for user in User.objects.filter(groups__name='shk')]
        
        for shk in shks:
            holiday_entitlement, not_taken_holidays, taken_holidays_days, remaining_holidays = calc_holiday(shk.user)
            shks_data.append({
                'contract': shk,
                'remaining_holidays': remaining_holidays,
            })
        holidays = Holiday.objects.filter(by_id__in=[shk.user for shk in shks]).order_by('-from_date')
        
        context = {
            'segment': 'holidays',
            'holidays': holidays,
            'shks_data': shks_data,
        }
        
        html_template = loader.get_template('home/holidays_supervisor.html')
    else:
        # process form
        if request.method == 'POST':
            if request.POST["formType"] == "newHoliday":
                h = Holiday(by_id = logged_user, from_date = request.POST["from_date"], to_date = request.POST["to_date"])
                if h.from_date < h.to_date:
                    h.save()
            elif request.POST["formType"] == "editHoliday":
                h = Holiday.objects.get(id=request.POST["holidayId"])
                h.from_date = request.POST["from_date"]
                h.to_date = request.POST["to_date"]
                if h.from_date < h.to_date:
                    h.save()
                    
        holiday_entitlement, not_taken_holidays, taken_holidays_days, remaining_holidays = calc_holiday(logged_user)
        taken_holidays = Holiday.objects.filter(by_id=logged_user)
        
        context = {
            'segment': 'holidays',
            'holiday_entitlement': holiday_entitlement,
            'not_taken': not_taken_holidays,
            'taken': taken_holidays_days,
            'remaining': remaining_holidays,
            'holidays': taken_holidays,
        }
        
        html_template = loader.get_template('home/holidays.html')
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def editHoliday(request: HttpRequest, holiday_id: int):
    logged_user = request.user
    holiday = get_object_or_404(Holiday, pk=holiday_id, by_id=logged_user)
    
    context = {
        'segment': 'editHoliday',
        'holiday': holiday,
    }
    
    html_template = loader.get_template('home/editHoliday.html')
    return HttpResponse(html_template.render(context, request))

@login_required(login_url="/login/")
def pages(request: HttpRequest):
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
