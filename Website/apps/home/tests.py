from django.test import TestCase

import datetime as dt
from freezegun import freeze_time

from .models import Holiday, Contract, Task, ContractChange
from django.contrib.auth.models import User
from .views import calc_holiday, calc_days_to_work, calc_working_time, get_free_days, business_days, get_employment_time, do_carryover, working_hours_on_day

# Create your tests here.

class FunctionsTests(TestCase):
    @freeze_time("2023-07-01")
    def test_holiday_one_standard_contract(self):
        """Test if a holiday is calculated correctly for a standard contract: 5 hours per week, one semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5)
        self.assertEqual(calc_holiday(u), (10.0, 0.0, 0, 10.0))
    
    @freeze_time("2023-07-01") 
    def test_holiday_one_contract_10_hours(self):
        """Test if a holiday is calculated correctly for a contract: 10 hours per week, one semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=10)
        self.assertEqual(calc_holiday(u), (10.0, 0.0, 0, 10.0))
    
    @freeze_time("2023-07-01")   
    def test_holiday_two_standard_contracts(self):
        """Test if a holiday is calculated correctly for two contracts: 2x 5 hours per week, one semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5)
        c2 = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5)
        self.assertEqual(calc_holiday(u), (20.0, 0.0, 0, 20.0))
    
    @freeze_time("2023-07-01") 
    def test_holiday_two_standard_contracts_different_duration(self):
        """Test if a holiday is calculated correctly for two contracts: 2x 5 hours per week, partial semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5) # 6 months
        c2 = Contract.objects.create(user=u, contract_start_date='2023-07-01', contract_end_date='2023-09-30', hours_per_week=5) # 3 months
        self.assertEqual(calc_holiday(u), (15.0, 0.0, 0, 15.0))
    
    @freeze_time("2023-07-01")  
    def test_holiday_one_standard_contract_carryover_same_hours(self):
        """Test if a holiday is calculated correctly for a standard contract: 5 hours per week, one semester, but in last semester 2 holidays were not taken, last semester 5 hours per week -> 2 holiday hours not taken
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5, carry_over_holiday_hours_from_last_semester=2)
        self.assertEqual(calc_holiday(u), (10.0, 2.0, 0, 12.0))
    
    @freeze_time("2023-07-01")  
    def test_holiday_one_contract_10_hours_carryover_different_hours(self):
        """Test if a holiday is calculated correctly for a contract: 10 hours per week, one semester, but in last semester 2 holidays were not taken, last semester 5 hours per week -> 2 holiday hours not taken. These 2 hours are equivalent to 1 holiday day in this semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=10, carry_over_holiday_hours_from_last_semester=2)
        self.assertEqual(calc_holiday(u), (10.0, 1.0, 0, 11.0))
    
    @freeze_time("2023-07-01")   
    def test_holiday_one_standard_contract_carryover_negative_holiday(self):
        """Test if a holiday is calculated correctly for a standard contract: 5 hours per week, one semester, but in last semester 2 holidays more taken than entitled, last semester 5 hours per week -> -2 holiday hours not taken
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5, carry_over_holiday_hours_from_last_semester=-2)
        self.assertEqual(calc_holiday(u), (10.0, -2.0, 0, 8.0))
    
    @freeze_time("2023-07-01")   
    def test_holiday_one_standard_contract_holiday_taken(self):
        """Test if a holiday is calculated correctly for a standard contract: 5 hours per week, one semester, 2 holiday days taken
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5)
        h = Holiday.objects.create(from_date='2023-05-02', to_date='2023-05-03', by_id=u)
        self.assertEqual(calc_holiday(u), (10.0, 0.0, 2, 8.0))
    
    @freeze_time("2023-07-01") 
    def test_holiday_one_standard_contract_holiday_taken_over_free_days(self):
        """Test if a holiday is calculated correctly for a standard contract: 5 hours per week, one semester, 1 holiday day taken (1st of May is free anyway)
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5)
        h = Holiday.objects.create(from_date='2023-05-01', to_date='2023-05-02', by_id=u)
        self.assertEqual(calc_holiday(u), (10.0, 0.0, 1, 9.0))
        
    def test_free_days(self):
        """Test if the correct number of free days between to dates is calculated. In this case, 1st of May is a holiday and 2nd of May is a normal working day. -> 1 free day
        """
        free_days = get_free_days(dt.date(2023,5,1), dt.date(2023,5,2))
        self.assertEqual(len(free_days.keys()), 1)
      
    def test_business_days_week(self):
        """Test if the correct number of business days between to dates is calculated. 2 days
        """
        bdays = business_days(dt.date(2023,5,1), dt.date(2023,5,2))
        self.assertEqual(bdays, 2)
    
    def test_business_days_weekend(self):
        """Test if the correct number of business days between to dates is calculated. End day is saturday
        """
        bdays = business_days(dt.date(2023,5,5), dt.date(2023,5,6))
        self.assertEqual(bdays, 1)
       
    def test_business_days_weekend(self):
        """Test if the correct number of business days between to dates is calculated. End day is sunday
        """
        bdays = business_days(dt.date(2023,5,5), dt.date(2023,5,7))
        self.assertEqual(bdays, 1)
     
    def test_business_days_weekend(self):
        """Test if the correct number of business days between to dates is calculated. End day is monday
        """
        bdays = business_days(dt.date(2023,5,5), dt.date(2023,5,8))
        self.assertEqual(bdays, 2)
     
    def test_business_days_weekend(self):
        """Test if the correct number of business days between to dates is calculated. Start day is weekend
        """
        bdays = business_days(dt.date(2023,5,7), dt.date(2023,5,8))
        self.assertEqual(bdays, 1)
    
    @freeze_time("2023-07-01")    
    def test_days_to_work(self):
        """Test if the correct number of days to work of a contract is calculated. Contract is already over, so 5 days to work
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        self.assertEqual(calc_days_to_work(c.contract_start_date, c.contract_end_date), 5)
    
    @freeze_time("2023-07-02")    
    def test_days_to_work_holiday(self):
        """Test if the correct number of days to work of a contract is calculated. 1 week with 1 free day
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,5,1), contract_end_date=dt.date(2023,5,7), hours_per_week=5) # 1 week
        self.assertEqual(calc_days_to_work(c.contract_start_date, c.contract_end_date), 4)
    
    @freeze_time("2023-07-13")    
    def test_hours_to_work_no_work(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, so 5 hours to work
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        self.assertEqual(calc_working_time(u), (5.0, 0.0, 0.0, 5.0))
    
    @freeze_time("2023-07-13")    
    def test_hours_to_work_no_work_holiday(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, 1 day holiday taken, so 4 hours to work
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        h = Holiday.objects.create(from_date='2023-06-13', to_date='2023-06-13', by_id=u)
        self.assertEqual(calc_working_time(u), (4.0, 0.0, 0.0, 4.0))
    
    @freeze_time("2023-06-02")    
    def test_hours_to_work_no_work_holiday_free_day(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, 1 day holiday taken, 1 free day, so 3 hours to work
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,5,1), contract_end_date=dt.date(2023,5,7), hours_per_week=5) # 1 week
        h = Holiday.objects.create(from_date='2023-05-02', to_date='2023-05-02', by_id=u)
        self.assertEqual(calc_working_time(u), (3.0, 0.0, 0.0, 3.0))
    
    @freeze_time("2023-07-13")    
    def test_hours_to_work_task_finished(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, so 5 hours to work, 1 task with 2 hours worked on it
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        t = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,18))
        self.assertEqual(calc_working_time(u), (5.0, 2.0, 2.0, 3.0))
    
    @freeze_time("2023-07-13")    
    def test_hours_to_work_task_not_finished(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, so 5 hours to work, 1 task with 2 hours worked on it but not finished (4 hours total time)
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        t = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=4, worked_hours=2, deadline=dt.date(2023,6,18))
        self.assertEqual(calc_working_time(u), (5.0, 2.0, 4.0, 3.0))
    
    @freeze_time("2023-07-13")    
    def test_hours_to_work_contract_change(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, so 5 hours to work, and was changed for one day to 10 hours per week -> 6 hours to work
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        cc = ContractChange.objects.create(contract_id=c, from_date=dt.date(2023,6,13), to_date=dt.date(2023,6,13), hours_per_week=10)
        self.assertEqual(calc_working_time(u), (6.0, 0.0, 0.0, 6.0))
    
    @freeze_time("2023-08-13")    
    def test_hours_to_work_contract_change_weekend(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, so 5 hours to work, and was changed for one day (weekend) to 10 hours per week -> 5 hours to work
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        cc = ContractChange.objects.create(contract_id=c, from_date=dt.date(2023,6,17), to_date=dt.date(2023,6,17), hours_per_week=10)
        self.assertEqual(calc_working_time(u), (5.0, 0.0, 0.0, 5.0))
    
    @freeze_time("2023-08-13")    
    def test_hours_to_work_contract_change_open_end(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, so 5 hours to work, and was changed middle of the week to 10 hours per week (open end = till end of contract) -> 8 hours to work
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        cc = ContractChange.objects.create(contract_id=c, from_date=dt.date(2023,6,14), hours_per_week=10)
        self.assertEqual(calc_working_time(u), (8.0, 0.0, 0.0, 8.0))
    
    @freeze_time("2023-08-13")    
    def test_hours_to_work_contract_change_two_changes_open_end(self):
        """Test if the correct number of hours to work of a contract is calculated. Contract is one week long, so 5 hours to work, and was changed middle of the week to 10 hours per week and later changed to 20 hours per week -> 12 hours to work
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5) # 1 week
        cc1 = ContractChange.objects.create(contract_id=c, from_date=dt.date(2023,6,14), to_date=dt.date(2023,6,14), hours_per_week=10)
        cc2 = ContractChange.objects.create(contract_id=c, from_date=dt.date(2023,6,15), hours_per_week=20)
        self.assertEqual(calc_working_time(u), (12.0, 0.0, 0.0, 12.0))
    
    @freeze_time("2023-06-22")    
    def test_employment_time_standard_contract(self):
        """User has one standard contract, so employment time is from contract start date to contract end date, a second contract was made but it is in the middle of the first contract, so it is not relevant for the employment time
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,4,1), contract_end_date=dt.date(2023,9,30), hours_per_week=5)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,15), contract_end_date=dt.date(2023,6,24), hours_per_week=5)
        self.assertEqual(get_employment_time(u), (dt.date(2023,4,1), dt.date(2023,9,30)))
    
    @freeze_time("2023-06-22")    
    def test_employment_time_extending(self):
        """User has contract, so employment time is from contract start date to contract end date, a second contract was made which extends over the first contract
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,4,1), contract_end_date=dt.date(2023,8,30), hours_per_week=5)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,5,1), contract_end_date=dt.date(2023,9,30), hours_per_week=5)
        self.assertEqual(get_employment_time(u), (dt.date(2023,4,1), dt.date(2023,9,30)))
        
    @freeze_time("2023-06-22")    
    def test_employment_time_last_semester_contract(self):
        """User has standard contract and a contract from last semester which should be ignored
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,4,1), contract_end_date=dt.date(2023,9,30), hours_per_week=5)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2022,10,1), contract_end_date=dt.date(2023,3,30), hours_per_week=5)
        self.assertEqual(get_employment_time(u), (dt.date(2023,4,1), dt.date(2023,9,30)))
        
    @freeze_time("2023-10-01")    
    def test_employment_time_after_semester(self):
        """User has finished contract, semester is over, employment time is last semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,4,1), contract_end_date=dt.date(2023,9,30), hours_per_week=5)
        self.assertEqual(get_employment_time(u), (dt.date(2023,4,1), dt.date(2023,9,30)))
        
    @freeze_time("2023-06-30")    
    def test_working_time_task_done_in_last_contract(self):
        """User had contract last week, did a task there, but it is not relevant for this week's contract
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=5)
        t = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,23)) # should be ignored
        self.assertEqual(calc_working_time(u), (5.0, 0, 0, 5.0))
        
    @freeze_time("2023-06-26")
    def test_do_carryover_simple(self):
        """User had contract last week, did a task there and got a contract for this week, so the 3 hours from last week should be carried over to this week
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5)
        t = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,23))
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        self.assertEqual(do_carryover(u), (3.0, 0.0))
        
    @freeze_time("2023-06-27")
    def test_do_carryover_multiple_last_contracts(self):
        """User had contracts for last weeks, did a task there and got a contract for this week, so the 3 hours from last week should be carried over to this week
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,5), contract_end_date=dt.date(2023,6,11), hours_per_week=5)
        t1 = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,11))
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,12), contract_end_date=dt.date(2023,6,18), hours_per_week=5, carry_over_hours_from_last_semester=3)
        t2 = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,18))
        c3 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,25), hours_per_week=5, carry_over_hours_from_last_semester=6)
        t3 = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,25))
        c4 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,7,2), hours_per_week=5)
        self.assertEqual(do_carryover(u), (9.0, 0.0))
        
    @freeze_time("2023-06-26")
    def test_do_carryover_multiple_last_contracts(self):
        """User had 2 contracts last week, did a task there and got a contract for this week, so the 8 hours from last week should be carried over to this week
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c10 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5)
        c11 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5)
        t = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,23))
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        self.assertEqual(do_carryover(u), (8.0, 0.0))
        
    @freeze_time("2023-06-26")
    def test_do_carryover_multiple_last_contracts_previous_carryover(self):
        """User had 2 contracts last week, did a task there and got a contract for this week, so the 11 hours from last week should be carried over to this week
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c10 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5, carry_over_hours_from_last_semester=1)
        c11 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5, carry_over_hours_from_last_semester=2)
        t = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,23))
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        self.assertEqual(do_carryover(u), (11.0, 0.0))
        
    @freeze_time("2023-06-26")
    def test_do_carryover_multiple_last_contracts_previous_carryover_holidays(self):
        """User had 2 contracts last week, did a task there and got a contract for this week, so the 11 hours from last week should be carried over to this week. Additionally holiday carryovers (no holiday entitlement for so short contracts)
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c10 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5, carry_over_hours_from_last_semester=1, carry_over_holiday_hours_from_last_semester=4)
        c11 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5, carry_over_hours_from_last_semester=2, carry_over_holiday_hours_from_last_semester=5)
        t = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,23))
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        self.assertEqual(do_carryover(u), (11.0, 9.0))
        
    @freeze_time("2023-06-26")
    def test_do_carryover_multiple_last_contracts_previous_carryover_holidays_taken_holidays(self):
        """User had 2 contracts last week, did a task there and got a contract for this week, so the 10 (11 - 2 holiday) hours from last week should be carried over to this week. Additionally holiday carryovers (no holiday entitlement for so short contracts) but holidays taken
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c10 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5, carry_over_hours_from_last_semester=1, carry_over_holiday_hours_from_last_semester=4)
        c11 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,19), contract_end_date=dt.date(2023,6,23), hours_per_week=5, carry_over_hours_from_last_semester=2, carry_over_holiday_hours_from_last_semester=5)
        t = Task.objects.create(assigned_to=u, assigner=u, task_text='Test task', total_hours=2, worked_hours=2, deadline=dt.date(2023,6,23))
        h = Holiday.objects.create(from_date='2023-06-20', to_date='2023-06-20', by_id=u)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        self.assertEqual(do_carryover(u), (9.0, 7.0))
        
    def test_working_hours_day_simple(self):
        """User has contract with 10 hours per week, so 2 hours per day
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        self.assertEqual(working_hours_on_day(u, dt.date(2023,6,26)), 2.0)
        
    def test_working_hours_day_two_contracts(self):
        """User has 2 contracts with 10 hours per week, so 4 hours per day
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        self.assertEqual(working_hours_on_day(u, dt.date(2023,6,26)), 4.0)
        
    def test_working_hours_day_two_contracts_contract_change(self):
        """User has 2 contracts with 10 hours per week + one contract change, so 6 hours per day
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,6,26), contract_end_date=dt.date(2023,6,30), hours_per_week=10)
        cc = ContractChange.objects.create(contract_id=c2, from_date=dt.date(2023,6,26), to_date=dt.date(2023,6,26), hours_per_week=20)
        self.assertEqual(working_hours_on_day(u, dt.date(2023,6,26)), 6.0)
        
    def test_working_hours_day_free_day(self):
        """User has 2 contracts with 10 hours per week + one contract change, so 6 hours per day but we check on 1st May (free day), so 0 hours per day
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,5,1), contract_end_date=dt.date(2023,5,7), hours_per_week=10)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,5,1), contract_end_date=dt.date(2023,5,7), hours_per_week=10)
        cc = ContractChange.objects.create(contract_id=c2, from_date=dt.date(2023,5,1), to_date=dt.date(2023,5,1), hours_per_week=20)
        self.assertEqual(working_hours_on_day(u, dt.date(2023,5,1)), 0.0)
        
    def test_working_hours_day_weekend(self):
        """User has 2 contracts with 10 hours per week + one contract change, so 6 hours per day but we check on weekend, so 0 hours per day
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,5,1), contract_end_date=dt.date(2023,5,7), hours_per_week=10)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,5,1), contract_end_date=dt.date(2023,5,7), hours_per_week=10)
        cc = ContractChange.objects.create(contract_id=c2, from_date=dt.date(2023,5,1), to_date=dt.date(2023,5,1), hours_per_week=20)
        self.assertEqual(working_hours_on_day(u, dt.date(2023,5,7)), 0.0)
        
    def test_working_hours_day_contract_over(self):
        """User had contracts before but these are inactive. Active is just one 10-hour-contract, so 2 hours per day
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date=dt.date(2023,5,1), contract_end_date=dt.date(2023,5,7), hours_per_week=10)
        c2 = Contract.objects.create(user=u, contract_start_date=dt.date(2022,6,26), contract_end_date=dt.date(2022,6,30), hours_per_week=10)
        cc = ContractChange.objects.create(contract_id=c2, from_date=dt.date(2022,6,26), to_date=dt.date(2022,6,26), hours_per_week=20)
        self.assertEqual(working_hours_on_day(u, dt.date(2023,5,2)), 2.0)