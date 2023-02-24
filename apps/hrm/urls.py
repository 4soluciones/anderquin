from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.hrm.views import *

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('employee_list/', login_required(EmployeeList.as_view()), name='employee_list'),
    path('json_employee_create/', login_required(JsonEmployeeCreate.as_view()), name='json_employee_create'),
    path('json_employee_list/', login_required(JsonEmployeeList.as_view()), name='json_employee_list'),
    path('json_employee_edit/<int:pk>/',
         login_required(JsonEmployeeUpdate.as_view()), name='json_employee_edit'),
    path('get_worker_designation/', get_worker_designation, name='get_worker_designation'),
    path('create_worker/', create_worker, name='create_worker'),
    path('get_establishment_code/', get_establishment_code, name='get_establishment_code'),
    path('get_worker_establishment/', get_worker_establishment, name='get_worker_establishment'),
    path('update_worker_establishment/', update_worker_establishment, name='update_worker_establishment'),
    path('get_worker_user/', get_worker_user, name='get_worker_user'),
    path('update_worker_user/', update_worker_user, name='update_worker_user'),
    path('edit_worker_designation/', edit_worker_designation, name='edit_worker_designation'),
    path('update_worker/', login_required(update_worker), name='update_worker'),
]
