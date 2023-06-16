# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.test import TestCase

from .models import Holiday, Contract, Task
from django.contrib.auth.models import User
from .views import calc_holiday, calc_days_to_work, calc_working_time

# Create your tests here.

class FunctionsTests(TestCase):
    def test_holiday_one_standard_contract(self):
        """Test if a holiday is calculated correctly for a standard contract: 5 hours per week, one semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5)
        self.assertEqual(calc_holiday(u), (10.0, 0.0, 0, 10.0))
        
    def test_holiday_one_contract_10_hours(self):
        """Test if a holiday is calculated correctly for a contract: 10 hours per week, one semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=10)
        self.assertEqual(calc_holiday(u), (10.0, 0.0, 0, 10.0))
        
    def test_holiday_two_standard_contracts(self):
        """Test if a holiday is calculated correctly for two contracts: 2x 5 hours per week, one semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c1 = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5)
        c2 = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5)
        self.assertEqual(calc_holiday(u), (20.0, 0.0, 0, 20.0))
        
    def test_holiday_one_standard_contract_carryover_same_hours(self):
        """Test if a holiday is calculated correctly for a standard contract: 5 hours per week, one semester, but in last semester 2 holidays were not taken, last semester 5 hours per week -> 2 holiday hours not taken
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5, carry_over_holiday_hours_from_last_semester=2)
        self.assertEqual(calc_holiday(u), (10.0, 2.0, 0, 12.0))
        
    def test_holiday_one_contract_10_hours_carryover_different_hours(self):
        """Test if a holiday is calculated correctly for a contract: 10 hours per week, one semester, but in last semester 2 holidays were not taken, last semester 5 hours per week -> 2 holiday hours not taken. These 2 hours are equivalent to 1 holiday day in this semester
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=10, carry_over_holiday_hours_from_last_semester=2)
        self.assertEqual(calc_holiday(u), (10.0, 1.0, 0, 11.0))
        
    def test_holiday_one_standard_contract_carryover_negative_holiday(self):
        """Test if a holiday is calculated correctly for a standard contract: 5 hours per week, one semester, but in last semester 2 holidays more taken than entitled, last semester 5 hours per week -> -2 holiday hours not taken
        """
        u = User.objects.create_user(username='testuser', password='12345', email='test@example.com')
        c = Contract.objects.create(user=u, contract_start_date='2023-04-01', contract_end_date='2023-09-30', hours_per_week=5, carry_over_holiday_hours_from_last_semester=-2)
        self.assertEqual(calc_holiday(u), (10.0, -2.0, 0, 8.0))