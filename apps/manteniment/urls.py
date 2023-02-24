from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.buys.views import *

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('purchase_form/', purchase_form, name='purchase_form'),
    path('save_purchase/', save_purchase, name='save_purchase'),
    path('requirement_buy_create/', requirement_buy_create, name='requirement_buy_create'),
    path('requirement_buy_save/', requirement_buy_save, name='requirement_buy_save'),
    path('requirement_buy_list/', login_required(get_requeriments_buys_list), name='requirement_buy_list'),
    path('get_purchase_list/', get_purchase_list, name='get_purchase_list'),
    path('get_detail_purchase_store/', get_detail_purchase_store, name='get_detail_purchase_store'),
    path('get_requirement_programming/', get_requirement_programming, name='get_requirement_programming'),
    path('get_programming_invoice/', get_programming_invoice, name='get_programming_invoice'),
    path('save_detail_purchase_store/', save_detail_purchase_store, name='save_detail_purchase_store'),
    path('save_programming_buys/', save_programming_buys, name='save_programming_buys'),
    path('get_units_by_product/', get_units_by_product, name='get_units_by_product'),
    path('get_scop_truck/', get_scop_truck, name='get_scop_truck'),
    path('save_programming_invoice/', save_programming_invoice, name='save_programming_invoice'),
    path('save_detail_requirement_store/', save_detail_requirement_store, name='save_detail_requirement_store'),
    path('get_expense_programming/', get_expense_programming, name='get_expense_programming'),
    path('save_programming_fuel/', save_programming_fuel, name='save_programming_fuel'),
    path('get_approve_detail_requirement/', get_approve_detail_requirement, name='get_approve_detail_requirement'),
    path('update_details_requirement_store/', update_details_requirement_store, name='update_details_requirement_store'),
    path('get_products_by_requirement/', get_products_by_requirement, name='get_products_by_requirement'),
    path('get_list_requirement_stock/', get_list_requirement_stock, name='get_list_requirement_stock'),
    path('get_requirement_balance/', get_requirement_balance, name='get_requirement_balance'),
    path('get_programming_by_truck_and_dates/', get_programming_by_truck_and_dates, name='get_programming_by_truck_and_dates'),
    path('get_report_kardex_glp/', get_report_kardex_glp, name='get_report_kardex_glp'),
    path('get_rateroutes_programming/', get_rateroutes_programming, name='get_rateroutes_programming'),
]
