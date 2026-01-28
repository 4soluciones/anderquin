from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.accounting.views import *
from apps.accounting.views_PDF import print_pdf_bill_finances, print_pdf_purchases_report, export_excel_purchases_report

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('get_purchases_list/', login_required(get_purchases_list), name='get_purchases_list'),
    path('get_dict_purchases/', login_required(get_dict_purchases), name='get_dict_purchases'),
    path('get_purchases_by_date/', login_required(get_purchases_by_date), name='get_purchases_by_date'),
    path('get_purchases_paid_by_date/', login_required(get_purchases_paid_by_date), name='get_purchases_paid_by_date'),
    path('new_opening_balance/', login_required(new_opening_balance), name='new_opening_balance'),
    path('get_purchases_pay/', login_required(get_purchases_pay), name='get_purchases_pay'),
    path('new_payment_purchase/', login_required(new_payment_purchase), name='new_payment_purchase'),
    path('edit_file/', login_required(edit_file), name='edit_file'),

    # cash
    path('get_cash_control_list/', login_required(get_cash_control_list), name='get_cash_control_list'),
    path('open_cash/', login_required(open_cash), name='open_cash'),
    path('close_cash/', login_required(close_cash), name='close_cash'),
    path('get_initial_balance/', login_required(get_initial_balance), name='get_initial_balance'),
    path('get_cash_date/', login_required(get_cash_date), name='get_cash_date'),
    path('update_description_cash/', login_required(update_description_cash), name='update_description_cash'),


    # accounts
    path('get_account_list/', login_required(get_account_list), name='get_account_list'),
    path('get_accounts_by_type/', login_required(get_accounts_by_type), name='get_accounts_by_type'),
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
    path('get_cash_flow_for_edit/', login_required(get_cash_flow_for_edit), name='get_cash_flow_for_edit'),
    path('update_cash_flow/', login_required(update_cash_flow), name='update_cash_flow'),
    path('cancel_cash_flow/', login_required(cancel_cash_flow), name='cancel_cash_flow'),

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

    # BUYS
    path('get_purchases_with_bill/', login_required(get_purchases_with_bill), name='get_purchases_with_bill'),
    path('get_purchase_list_finances/', login_required(get_purchase_list_finances), name='get_purchase_list_finances'),
    path('modal_bill_create/', login_required(modal_bill_create), name='modal_bill_create'),
    path('save_bill/', login_required(save_bill), name='save_bill'),
    path('cancel_bill/', login_required(cancel_bill), name='cancel_bill'),
    path('get_bill/', login_required(get_bill), name='get_bill'),
    path('get_product_units/', login_required(get_product_units), name='get_product_units'),
    path('print_pdf_bill_finances/<int:pk>/', print_pdf_bill_finances, name='print_pdf_bill_finances'),
    
    # Reportes PDF y Excel
    path('print_pdf_purchases_report/', login_required(print_pdf_purchases_report), name='print_pdf_purchases_report'),
    path('export_excel_purchases_report/', login_required(export_excel_purchases_report), name='export_excel_purchases_report'),

]
