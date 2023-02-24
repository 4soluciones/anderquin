from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.buys.views import *
from apps.buys.views_PDF import kardex_glp_pdf, print_requirement

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('purchase_form/', purchase_form, name='purchase_form'),
    path('save_purchase/', save_purchase, name='save_purchase'),

    #COMPRAS NORMALES
    path('get_purchase_list/', get_purchase_list, name='get_purchase_list'),
    path('get_purchase_annular_list/', get_purchase_annular_list, name='get_purchase_annular_list'),
    path('get_purchase_store_list/', get_purchase_store_list, name='get_purchase_store_list'),
    path('get_detail_purchase_store/', get_detail_purchase_store, name='get_detail_purchase_store'),
    path('get_details_by_purchase/', get_details_by_purchase, name='get_details_by_purchase'),

    path('get_requirement_programming/', get_requirement_programming, name='get_requirement_programming'),
    path('get_programming_invoice/', get_programming_invoice, name='get_programming_invoice'),
    path('save_detail_purchase_store/', save_detail_purchase_store, name='save_detail_purchase_store'),
    path('get_units_by_product/', get_units_by_product, name='get_units_by_product'),
    path('get_scop_truck/', get_scop_truck, name='get_scop_truck'),
    path('save_programming_invoice/', save_programming_invoice, name='save_programming_invoice'),
    path('save_detail_requirement_store/', save_detail_requirement_store, name='save_detail_requirement_store'),
    path('get_expense_programming/', get_expense_programming, name='get_expense_programming'),
    path('save_programming_fuel/', save_programming_fuel, name='save_programming_fuel'),
    path('get_approve_detail_requirement/', get_approve_detail_requirement, name='get_approve_detail_requirement'),
    path('update_details_requirement_store/', update_details_requirement_store, name='update_details_requirement_store'),
    path('update_state_annular_purchase/', update_state_annular_purchase, name='update_state_annular_purchase'),
    path('get_products_by_requirement/', get_products_by_requirement, name='get_products_by_requirement'),
    path('get_list_requirement_stock/', get_list_requirement_stock, name='get_list_requirement_stock'),
    path('get_requirement_balance/', get_requirement_balance, name='get_requirement_balance'),
    path('get_programming_by_truck_and_dates/', get_programming_by_truck_and_dates, name='get_programming_by_truck_and_dates'),
    path('get_report_kardex_glp/', get_report_kardex_glp, name='get_report_kardex_glp'),
    path('get_rateroutes_programming/', get_rateroutes_programming, name='get_rateroutes_programming'),
    # path('SalesList/<int:pk>/', SalesList, name='SalesList'),
    path('kardex_glp_pdf/<str:date_initial>/<str:date_final>/', kardex_glp_pdf, name='kardex_glp_pdf'),
    # path('kardex_glp_pdf/', kardex_glp_pdf, name='kardex_glp_pdf'),
    #requerimientos GLP
    path('requirement_buy_create/', requirement_buy_create, name='requirement_buy_create'),
    path('create_requirement_view/', login_required(create_requirement_view), name='create_requirement_view'),
    path('save_requirement/', login_required(save_requirement), name='save_requirement'),
    path('requirement_buy_save/', requirement_buy_save, name='requirement_buy_save'),
    path('requirement_buy_list/', login_required(get_requeriments_buys_list), name='requirement_buy_list'),
    path('get_requirements_buys_list_approved/', get_requirements_buys_list_approved, name='get_requirements_buys_list_approved'),
    path('save_programming_buys/', save_programming_buys, name='save_programming_buys'),
    path('get_units_product/', get_units_product, name='get_units_product'),

    # ReportLab
    path('print_requirement/<int:pk>/', print_requirement, name='print_requirement'),

    # Payment_Approved
    path('get_modal_payment_buys_approved/', get_modal_payment_buys_approved, name='get_modal_payment_buys_approved'),
    path('new_loan_payment_buys_approved/', new_loan_payment_buys_approved, name='new_loan_payment_buys_approved'),
    path('get_programming_pay/', get_programming_pay, name='get_programming_pay'),
    path('new_payment_programming_glp/', new_payment_programming_glp, name='new_payment_programming_glp'),
    path('get_programming_payment_table/', get_programming_payment_table, name='get_programming_payment_table'),

    # Report programmings all
    path('get_programmings_by_dates/', get_programmings_by_dates, name='get_programmings_by_dates'),
    # Report Graphic
    path('get_report_graphic_glp/', get_report_graphic_glp, name='get_report_graphic_glp'),

    # Report Buys
    path('report_purchases_all/', report_purchases_all, name='report_purchases_all'),
    path('report_purchases_by_supplier/', report_purchases_by_supplier, name='report_purchases_by_supplier'),
    path('get_purchases_by_license_plate/', get_purchases_by_license_plate, name='get_purchases_by_license_plate'),
    path('get_purchases_by_provider_category/', get_purchases_by_provider_category, name='get_purchases_by_provider_category'),
]
