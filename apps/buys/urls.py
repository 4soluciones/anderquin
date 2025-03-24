from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.buys.views import *

from apps.buys.views_PDF import print_pdf

urlpatterns = [
    # path('', login_required(Home.as_view()), name='home'),
    # path('purchase_form/', login_required(purchase_form), name='purchase_form'),
    path('save_purchase/', login_required(save_purchase), name='save_purchase'),

    # PURCHASES
    path('get_purchase_annular_list/', get_purchase_annular_list, name='get_purchase_annular_list'),
    path('update_state_annular_purchase/', update_state_annular_purchase, name='update_state_annular_purchase'),
    path('get_product/', get_product, name='get_product'),
    path('create_purchase/', create_purchase, name='create_purchase'),
    path('get_details_by_buy/', get_details_by_buy, name='get_details_by_buy'),
    path('buys_credit_note/', buys_credit_note, name='buys_credit_note'),

    path('purchases/', get_purchase_form, name='purchases'),

    path('get_units_product/', get_units_product, name='get_units_product'),

    # Report Buys
    path('report_purchases_all/', report_purchases_all, name='report_purchases_all'),
    path('report_purchases_by_supplier/', report_purchases_by_supplier, name='report_purchases_by_supplier'),
    path('get_purchases_by_provider_category/', get_purchases_by_provider_category,
         name='get_purchases_by_provider_category'),
    path('print_pdf_purchase_order/<int:pk>/', print_pdf, name='print_pdf_purchase_order'),

    # ORDER BUYS
    path('buy_list/', get_buy_list, name='buy_list'),
    path('buy_list/<int:contract_detail>/', get_buy_list, name='buy_list'),
    path('get_address_by_client_id/', get_address_by_client_id, name='get_address_by_client_id'),
    path('get_product_by_criteria_table/', get_product_by_criteria_table, name='get_product_by_criteria_table'),
    path('get_quantity_minimum/', get_quantity_minimum, name='get_quantity_minimum'),
    path('get_type_change/', get_type_change, name='get_type_change'),
    path('new_provider/', new_provider, name='new_provider'),
    path('get_sunat/', get_sunat, name='get_sunat'),
    path('save_provider/', save_provider, name='save_provider'),
    path('report_purchases_by_subsidiary/', report_purchases_by_subsidiary, name='report_purchases_by_subsidiary'),
    path('update_purchase/<int:pk>/', update_purchase, name='update_purchase'),
    path('save_update_purchase/', save_update_purchase, name='save_update_purchase'),
    path('get_correlative_by_year/', get_correlative_by_year, name='get_correlative_by_year'),
    path('buy_order_list/', get_buy_order_list, name='buy_order_list'),
    path('buy_order_store_list/', get_buy_order_store_list, name='buy_order_store_list'),
    path('get_detail_purchase_store/', get_detail_purchase_store, name='get_detail_purchase_store'),
    path('save_detail_buy_order_store/', save_detail_buy_order_store, name='save_detail_buy_order_store'),

    # DELETE DETAIL
    path('delete_item_buys/', login_required(delete_item_buys), name='delete_item_buys'),

    # SUPPLIERS
    path('suppliers/', login_required(supplier_list), name='supplier_list'),
    path('get_address_by_supplier_id/', get_address_by_supplier_id, name='get_address_by_supplier_id'),
    path('modal_supplier_create/', modal_supplier_create, name='modal_supplier_create'),
    path('save_supplier/', save_supplier, name='save_supplier'),
    path('modal_supplier_update/', modal_supplier_update, name='modal_supplier_update'),
    path('update_supplier/', update_supplier, name='update_supplier'),

    # CONTRACTS
    path('contracts/', contract_list, name='contract_list'),
    path('contract_list/', contract_list, name='contract_list'),
    path('modal_contract_create/', modal_contract_create, name='modal_contract_create'),
    path('save_contract/', save_contract, name='save_contract'),
    path('modal_update_contract/', modal_update_contract, name='modal_update_contract'),
    path('get_buys_by_contract/', login_required(get_buys_by_contract), name='get_buys_by_contract'),
    path('check_oc_update/', login_required(check_oc_update), name='check_oc_update'),
    path('save_update_contract/', login_required(save_update_contract), name='save_update_contract'),

    # ASIGNAR ALMACEN
    # path('assign_store_modal/', assign_store_modal, name='assign_store_modal'),

    # BILL
    path('bill/', login_required(bill_list), name='bill_list'),
    path('get_purchase_detail/', login_required(get_purchase_detail), name='get_purchase_detail'),
    path('get_purchases_by_client/', login_required(get_purchases_by_client), name='get_purchases_by_client'),
    # path('save_bill/', login_required(save_bill), name='save_bill'),
    # path('print_pdf_bill/<int:pk>/', print_pdf_bill, name='print_pdf_bill'),

    # GET CLIENT
    path('get_client/', login_required(get_client), name='get_client'),

    # GUIDE
    path('modal_new_guide/', login_required(modal_new_guide), name='modal_new_guide'),

    # REPORT CONTRACTS DETAIL
    path('contracts_detail/', login_required(report_contracts), name='contracts_detail'),

    # CREDIT NOTE
    path('save_credit_note/', login_required(save_credit_note), name='save_credit_note'),
]
