from django import template
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.template import loader
from django.urls import reverse
from django.shortcuts import get_object_or_404

from .models import Task, Holiday, Contract, ContractChange
from django.contrib.auth.models import User
from django.db.models import F

import datetime as dt
import numpy as np
import holidays as hd
from freezegun import freeze_time
from dateutil.rrule import rrule, DAILY

from typing import Tuple

def get_free_days(from_date: dt.date, to_date: dt.date) -> dict:
    """A function that returns all free days between two dates. It uses the holidays package to get all holidays in Saxony between the two dates. It returns a dictionary with the date as key and the name of the holiday as value.

    Args:
        from_date (dt.date): from date
        to_date (dt.date): to date

    Returns:
        dict: A dictionary with the date as key and the name of the holiday as value.
    """
    all_holidays = hd.country_holidays("DE", subdiv = "SN", years = [y for y in range(from_date.year, to_date.year + 1)])
    free_days = {}
    for date, name in sorted(all_holidays.items()):
        if from_date <= date <= to_date:
            free_days[date] = name
            
    return free_days

def get_employment_time(user: User) -> Tuple[dt.date, dt.date]:
    """A function that returns the start and end date of the current employment of a given user. It iterates over all contracts of the user and returns the earliest start date and the latest end date. If the user has no active contract, the start date is the start date of the last contract and the end date is the end date of the last contract.

    Args:
        user (User): The user for which the employment time should be calculated.

    Returns:
        Tuple[dt.date, dt.date]: The start and end date of the current employment.
    """
    start_dates = [contract.contract_start_date for contract in Contract.objects.filter(user=user) if contract.contract_start_date <= dt.date.today() <= contract.contract_end_date]
    end_dates = [contract.contract_end_date for contract in Contract.objects.filter(user=user) if contract.contract_start_date <= dt.date.today() <= contract.contract_end_date]
    if len(start_dates) == 0 or len(end_dates) == 0:
        start_date = Contract.objects.filter(user=user).order_by('-contract_end_date').first().contract_start_date
        end_date = Contract.objects.filter(user=user).order_by('-contract_end_date').first().contract_end_date
        return start_date, end_date
    
    return min(start_dates), max(end_dates)
            

def business_days(from_date: dt.date, to_date: dt.date) -> int:
    """A proper way to calculate the number of business days between 2 dates. np.busday_count does exclude the to_date but we want to include it. Therefore we add 1 if the to_date is not a weekend.

    Args:
        from_date (dt.date): from date
        to_date (dt.date): to date

    Returns:
        int: The number of business days between the two dates.
    """
    if to_date.weekday() >= 5:
        return np.busday_count(from_date, to_date)
    else:
        return np.busday_count(from_date, to_date) + 1

def calc_holiday(user: User) -> Tuple[float, float, int, float]:
    """This function calculates the holiday entitlement, the not taken holidays, the taken holidays and the remaining holidays for a given user. Since the holiday entitlement is calculated based on the contract duration, the function iterates over all contracts of the user. Important are the number of full months worked, for 12 months you get 20 days off.

    Args:
        user (User): The user for which the holiday entitlement should be calculated.

    Returns:
        Tuple[float, float, float, float]: holiday entitlement, not taken holidays in last semester, taken holidays days, remaining holidays in days
    """
    contracts = Contract.objects.filter(user=user, contract_start_date__range=get_employment_time(user), contract_end_date__range=get_employment_time(user))
    holiday_entitlement_sum, not_taken_holidays_sum = 0, 0
    for contract in contracts:
        contract_duration = dt.date(contract.contract_end_date.year, contract.contract_end_date.month, contract.contract_end_date.day) - dt.date(contract.contract_start_date.year, contract.contract_start_date.month, contract.contract_start_date.day)
        full_months = contract_duration.days // 30
        holiday_entitlement = round(full_months * 20 / 12,0)
        not_taken_holidays = contract.carry_over_holiday_hours_from_last_semester / contract.hours_per_week * 5
        holiday_entitlement_sum += holiday_entitlement
        not_taken_holidays_sum += not_taken_holidays
    
    taken_holidays = Holiday.objects.filter(by_id=user, from_date__range=get_employment_time(user), to_date__range=get_employment_time(user))
    taken_holidays_days = sum([business_days(holiday.from_date, holiday.to_date) - len(get_free_days(holiday.from_date, holiday.to_date).keys()) for holiday in taken_holidays])
    remaining_holidays = holiday_entitlement_sum + not_taken_holidays_sum - taken_holidays_days
    
    return holiday_entitlement_sum, not_taken_holidays_sum, taken_holidays_days, remaining_holidays

def calc_days_to_work(from_date: dt.date, to_date: dt.date) -> int:
    """This function calculates the number of days you should have worked until now. It uses the contract start date and the contract end date. If the contract end date is in the future, the current date is used instead.

    Args:
        from_date (dt.date): Beginning of the contract.
        to_date (dt.Date): End of the contract.

    Returns:
        int: number of days to work
    """
    free_days = len(get_free_days(from_date, min(dt.date.today(), to_date)).keys())
    days_to_work = business_days(from_date, min(dt.date.today(), to_date)) - free_days
    return days_to_work

def working_hours_on_day(user: User, date: dt.date) -> float:
    """Return the number of hours a user has to work on a given day

    Args:
        user (User): The user for which the working hours should be calculated.
        date (dt.date): The date for which the working hours should be calculated.

    Returns:
        float: The amount of hours to work on the given day.
    """
    free_days = get_free_days(date, date)
    
    # check if date is a free day
    if date in free_days.keys() or date.weekday() >= 5:
        return 0.0
    
    # find all contracts that are active on the given date
    hours_on_day = 0.0
    contracts = Contract.objects.filter(user=user, contract_start_date__lte=date, contract_end_date__gte=date)
    for contract in contracts:
        hours_on_day += contract.hours_per_week/5
        # find all contract changes that are active on the given date
        contract_changes = ContractChange.objects.filter(contract_id=contract, from_date__lte=date, to_date__gte=date)
        for contract_change in contract_changes:
            hours_on_day += contract_change.hours_per_week/5 - contract.hours_per_week/5
            
    return hours_on_day    

def calc_working_time(user: User) -> Tuple[float, float, float, float]:
    """This function calculates the hours to work, the worked hours, the planned hours and the excess hours for a given user. It uses the contract start date and the contract end date. If the contract end date is in the future, the current date is used instead. We do this for all contracts of the user and sum up the hours.

    Args:
        user (User): The user for which the working time should be calculated.

    Returns:
        Tuple[float, float, float, float]: hours to work, worked hours, planned hours, excess hours
    """
    contracts = Contract.objects.filter(user=user, contract_start_date__range=get_employment_time(user), contract_end_date__range=get_employment_time(user))
    hours_to_work = 0
    for contract in contracts:
        hours_to_work += calc_days_to_work(contract.contract_start_date, contract.contract_end_date) * contract.hours_per_week/5
        for contract_change in ContractChange.objects.filter(contract_id=contract, from_date__range=get_employment_time(user)):
            start_date = contract_change.from_date
            if contract_change.to_date is None:
                end_date = contract.contract_end_date
            else:
                end_date = contract_change.to_date
            hours_to_work += calc_days_to_work(start_date, end_date) * (contract_change.hours_per_week/5 - contract.hours_per_week/5)
        
    taken_holidays = Holiday.objects.filter(by_id=user, from_date__range=get_employment_time(user), to_date__range=get_employment_time(user))
    for holiday in taken_holidays:
        for day in rrule(DAILY, dtstart=holiday.from_date, until=holiday.to_date):
            hours_to_work -= working_hours_on_day(user, day.date())
    
    tasks = Task.objects.filter(assigned_to=user, deadline__range=get_employment_time(user))
    worked_hours = sum([task.worked_hours for task in tasks])
    planned_hours = sum([task.total_hours for task in tasks])
    excess_hours = hours_to_work - worked_hours
    
    return hours_to_work, worked_hours, planned_hours, excess_hours

def do_carryover(user: User) -> Tuple[float, float]:
    """Calculates carryover from last contract. This carryover will then be added to the carryover of the longest contract that is currently active.

    Args:
        user (User): The user for which the carryover should be calculated.

    Returns:
        Tuple[float, float]: carryover hours, carryover holiday hours
    """
    last_contracts_end_date = Contract.objects.filter(user=user, contract_end_date__lt=dt.date.today()).order_by('-contract_end_date').first().contract_end_date
    last_contracts = Contract.objects.filter(user=user, contract_end_date=last_contracts_end_date) # only nesseary because user can have multiple contracts ending at the same time
    with freeze_time(last_contracts_end_date): # want to use my functions but they only work during a contract
        hours_to_work, worked_hours, planned_hours, excess_hours = calc_working_time(user)
        holiday_entitlement_sum, not_taken_holidays_sum, taken_holidays_days, remaining_holidays = calc_holiday(user) # in days
        employment_start, employment_end = get_employment_time(user)
        average_hours_per_day = np.mean([working_hours_on_day(user, day.date()) for day in rrule(DAILY, dtstart=employment_start, until=employment_end)])
    
    carryover_hours = sum([contract.carry_over_hours_from_last_semester for contract in last_contracts]) + excess_hours
    carryover_holiday_hours = sum([contract.carry_over_holiday_hours_from_last_semester for contract in last_contracts]) + (holiday_entitlement_sum - taken_holidays_days) * average_hours_per_day
        
    # add carryover to carryover of longest contract
    longest_contract = Contract.objects.filter(user=user, contract_start_date__lte=dt.date.today(), contract_end_date__gte=dt.date.today()).extra(select={'duration': 'contract_end_date - contract_start_date'}).order_by('-duration').first()
    longest_contract.carry_over_hours_from_last_semester += carryover_hours
    longest_contract.carry_over_holiday_hours_from_last_semester += carryover_holiday_hours
    longest_contract.save()
        
    return carryover_hours, carryover_holiday_hours

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
            shks = Contract.objects.filter(supervisor=logged_user) # TODO: filter out shks that are not active anymore
        else:
            # get all shks
            # since a shk can have multiple contracts, we only get the first one
            shks = [Contract.objects.filter(user=user, contract_start_date__range=get_employment_time(user), contract_end_date__range=get_employment_time(user)).first() for user in User.objects.filter(groups__name='shk')]
        
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
        tasks = Task.objects.filter(assigned_to__in=[shk.user for shk in shks]).order_by('-deadline')[:10] # no filtering nessesary since we only get shks that are active
        
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
            'carry_over_hours_from_last_semester': sum([contract.carry_over_hours_from_last_semester for contract in Contract.objects.filter(user=logged_user, contract_start_date__range=get_employment_time(logged_user), contract_end_date__range=get_employment_time(logged_user))]),
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
        shks = Contract.objects.filter(supervisor=logged_user) # TODO: filter out shks that are not active anymore
        tasks = Task.objects.filter(assigned_to__in=[shk.user for shk in shks]).order_by('-deadline') # no filtering nessesary since we only get shks that are active
    elif is_shkofficer(logged_user):
        tasks = Task.objects.all().order_by('-deadline')
    else:
        tasks = Task.objects.filter(assigned_to=logged_user, deadline__range=get_employment_time(logged_user)).order_by('-deadline')
    
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
            shks = Contract.objects.filter(supervisor=logged_user) # TODO: filter out shks that are not active anymore
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
        holidays = Holiday.objects.filter(by_id__in=[shk.user for shk in shks]).order_by('-from_date') # no filtering nessesary since we only get shks that are active
        
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
        taken_holidays = Holiday.objects.filter(by_id=logged_user, from_date__range=get_employment_time(logged_user), to_date__range=get_employment_time(logged_user)).order_by('-from_date')
        
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
def contracts(request: HttpRequest):
    logged_user = request.user
    
    if is_shkofficer(logged_user):
        shks = User.objects.filter(groups__name='shk')
    elif is_supervisor(logged_user):
        shks = list(set([contract.user for contract in Contract.objects.filter(supervisor=logged_user)]))
    else:
        shks = User.objects.filter(id=logged_user.id)
    
    for shk in shks:
        shk.contracts = Contract.objects.filter(user=shk)
        for contract in shk.contracts:
            contract.contract_changes = ContractChange.objects.filter(contract_id=contract)
    
    context = {
        'segment': 'contracts',
        'shks': shks,
    }
    
    html_template = loader.get_template('home/contracts.html')
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
