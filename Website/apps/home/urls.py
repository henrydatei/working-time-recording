from django.urls import path, re_path
from apps.home import views

urlpatterns = [

    # The home page
    path('', views.index, name='home'),
    # AllTasks page
    path('tasks/', views.tasks, name='tasks'),
    # Edit task page
    path('editTask/<int:task_id>', views.editTask, name='editTask'),
    # Holiday page
    path('holidays/', views.holidays, name='holidays'),
    # Edit Holiday page
    path('editHoliday/<int:holiday_id>', views.editHoliday, name='editHoliday'),
    
    # AllContracts page
    path('contracts/', views.contracts, name='contracts'),

    # Matches any html file
    re_path(r'^.*\.*', views.pages, name='pages'),

]
