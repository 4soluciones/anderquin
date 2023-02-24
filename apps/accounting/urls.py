from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.accounting.views import *

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('get_purchases_list/', login_required(get_purchases_list), name='get_purchases_list'),
    path('get_dict_purchases/', login_required(get_dict_purchases), name='get_dict_purchases'),
    path('get_purchases_by_date/', login_required(get_purchases_by_date), name='get_purchases_by_date'),
    path('new_opening_balance/', login_required(new_opening_balance), name='new_opening_balance'),
    path('get_purchases_pay/', login_required(get_purchases_pay), name='get_purchases_pay'),
    path('new_payment_purchase/', login_required(new_payment_purchase), name='new_payment_purchase'),

    # cash
    path('get_cash_control_list/', login_required(get_cash_control_list), name='get_cash_control_list'),
    path('open_cash/', login_required(open_cash), name='open_cash'),
    path('close_cash/', login_required(close_cash), name='close_cash'),
    path('get_initial_balance/', login_required(get_initial_balance), name='get_initial_balance'),
    path('get_cash_date/', login_required(get_cash_date), name='get_cash_date'),
    path('update_description_cash/', login_required(update_description_cash), name='update_description_cash'),


    # accounts
    path('get_account_list/', login_required(get_account_list), name='get_account_list'),
    path('new_account/', login_required(new_account), name='new_account'),
    path('new_entity/', login_required(new_entity), name='new_entity'),
    path('get_entity/', login_required(get_entity), name='get_entity'),
    path('update_entity/', login_required(update_entity), name='update_entity'),

    # banks
    path('get_bank_control_list/', login_required(get_bank_control_list), name='get_bank_control_list'),
    path('update_description_and_date_cash_bank/', login_required(update_description_and_date_cash_bank), name='update_description_and_date_cash_bank'),
    path('get_modal_edit/', login_required(get_modal_edit), name='get_modal_edit'),

    # transactions
    path('new_bank_transaction/', login_required(new_bank_transaction), name='new_bank_transaction'),
    path('new_cash_disbursement/', login_required(new_cash_disbursement), name='new_cash_disbursement'),
    path('new_transfer_bank/', login_required(new_transfer_bank), name='new_transfer_bank'),
    path('get_cash_by_subsidiary/', login_required(get_cash_by_subsidiary), name='get_cash_by_subsidiary'),
    path('new_cash_transfer_to_cash/', login_required(new_cash_transfer_to_cash), name='new_cash_transfer_to_cash'),
    path('get_confirm_cash_to_cash_transfer/', login_required(get_confirm_cash_to_cash_transfer), name='get_confirm_cash_to_cash_transfer'),
    path('new_cash_to_bank/', login_required(new_cash_to_bank), name='new_cash_to_bank'),
    path('accept_cash_to_cash_transfer/', login_required(accept_cash_to_cash_transfer), name='accept_cash_to_cash_transfer'),
    path('desist_cash_to_cash_transfer/', login_required(desist_cash_to_cash_transfer), name='desist_cash_to_cash_transfer'),
    path('new_bank_to_cash_transfer/', login_required(new_bank_to_cash_transfer), name='new_bank_to_cash_transfer'),

    # reportes
    path('get_cash_report/', login_required(get_cash_report), name='get_cash_report'),
    path('get_cash_by_dates/', login_required(get_cash_by_dates), name='get_cash_by_dates'),
    path('update_transaction_date_in_cash_flow/', login_required(update_transaction_date_in_cash_flow), name='update_transaction_date_in_cash_flow'),

    # graphics
    path('get_graphic_cash_set_vs_purchase/', login_required(get_graphic_cash_set_vs_purchase), name='get_graphic_cash_set_vs_purchase'),

    # Salary
    path('get_report_employees_salary/', login_required(get_report_employees_salary), name='get_report_employees_salary'),
    path('get_salary_pay/', login_required(get_salary_pay), name='get_salary_pay'),
    path('new_payment_salary/', login_required(new_payment_salary), name='new_payment_salary'),

    # Tributes
    path('report_tributary/', login_required(report_tributary), name='report_tributary'),
    path('save_register_tributary/', login_required(save_register_tributary), name='save_register_tributary'),
]
