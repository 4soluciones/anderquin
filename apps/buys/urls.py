from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.buys.views import *
from apps.buys.views_PDF import kardex_glp_pdf, print_requirement

from apps.buys.views_PDF_purchase_order import print_pdf, print_pdf_bill

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('purchase_form/', login_required(purchase_form), name='purchase_form'),
    path('save_purchase/', login_required(save_purchase), name='save_purchase'),

    # COMPRAS NORMALES
    path('get_purchase_list/', get_purchase_list, name='get_purchase_list'),
    path('get_purchase_annular_list/', get_purchase_annular_list, name='get_purchase_annular_list'),
    path('get_purchase_store_list/', get_purchase_store_list, name='get_purchase_store_list'),
    path('get_detail_purchase_store/', get_detail_purchase_store, name='get_detail_purchase_store'),
    path('get_details_by_purchase/', get_details_by_purchase, name='get_details_by_purchase'),

    path('get_requirement_programming/', get_requirement_programming, name='get_requirement_programming'),
    path('get_programming_invoice/', get_programming_invoice, name='get_programming_invoice'),
    path('save_detail_purchase_store/', save_detail_purchase_store, name='save_detail_purchase_store'),
    path('get_units_by_product/', get_units_by_product, name='get_units_by_product'),
    path('get_price_by_unit/', get_price_by_unit, name='get_price_by_unit'),
    path('get_scop_truck/', get_scop_truck, name='get_scop_truck'),
    path('save_programming_invoice/', save_programming_invoice, name='save_programming_invoice'),
    path('save_detail_requirement_store/', save_detail_requirement_store, name='save_detail_requirement_store'),
    path('get_expense_programming/', get_expense_programming, name='get_expense_programming'),
    path('save_programming_fuel/', save_programming_fuel, name='save_programming_fuel'),
    path('get_approve_detail_requirement/', get_approve_detail_requirement, name='get_approve_detail_requirement'),
    path('update_details_requirement_store/', update_details_requirement_store,
         name='update_details_requirement_store'),
    path('update_state_annular_purchase/', update_state_annular_purchase, name='update_state_annular_purchase'),
    path('get_products_by_requirement/', get_products_by_requirement, name='get_products_by_requirement'),
    path('get_list_requirement_stock/', get_list_requirement_stock, name='get_list_requirement_stock'),
    path('get_requirement_balance/', get_requirement_balance, name='get_requirement_balance'),
    path('get_programming_by_truck_and_dates/', get_programming_by_truck_and_dates,
         name='get_programming_by_truck_and_dates'),
    path('get_report_kardex_glp/', get_report_kardex_glp, name='get_report_kardex_glp'),
    path('get_rateroutes_programming/', get_rateroutes_programming, name='get_rateroutes_programming'),
    # path('SalesList/<int:pk>/', SalesList, name='SalesList'),
    path('kardex_glp_pdf/<str:date_initial>/<str:date_final>/', kardex_glp_pdf, name='kardex_glp_pdf'),
    # path('kardex_glp_pdf/', kardex_glp_pdf, name='kardex_glp_pdf'),
    # requerimientos GLP
    path('requirement_buy_create/', requirement_buy_create, name='requirement_buy_create'),
    path('create_requirement_view/', login_required(create_requirement_view), name='create_requirement_view'),
    path('save_requirement/', login_required(save_requirement), name='save_requirement'),
    path('requirement_buy_save/', requirement_buy_save, name='requirement_buy_save'),
    path('requirement_buy_list/', login_required(get_requeriments_buys_list), name='requirement_buy_list'),
    path('get_requirements_buys_list_approved/', get_requirements_buys_list_approved,
         name='get_requirements_buys_list_approved'),
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
    path('get_purchases_by_provider_category/', get_purchases_by_provider_category,
         name='get_purchases_by_provider_category'),

    path('is_supplier_reference/', is_supplier_reference, name='is_supplier_reference'),
    path('is_entity_private/', is_entity_private, name='is_entity_private'),
    path('add_reference/', add_reference, name='add_reference'),
    path('add_address_entity/', add_address_entity, name='add_address_entity'),
    path('get_addresses_supplier/', get_addresses_supplier, name='get_addresses_supplier'),
    path('get_addresses_client/', get_addresses_client, name='get_addresses_client'),
    path('get_entities/', get_entities, name='get_entities'),
    path('print_pdf_purchase_order/<int:pk>/', print_pdf, name='print_pdf_purchase_order'),

    # NEW BUYS
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

    # DELETE DETAIL
    path('delete_item_buys/', login_required(delete_item_buys), name='delete_item_buys'),

    # PROVEEDORES
    path('suppliers/', login_required(supplier_list), name='supplier_list'),
    path('get_address_by_supplier_id/', get_address_by_supplier_id, name='get_address_by_supplier_id'),
    path('modal_supplier_create/', modal_supplier_create, name='modal_supplier_create'),
    path('save_supplier/', save_supplier, name='save_supplier'),
    path('modal_supplier_update/', modal_supplier_update, name='modal_supplier_update'),
    path('update_supplier/', update_supplier, name='update_supplier'),

    # CONTRATOS
    path('contracts/', contract_list, name='contract_list'),
    path('modal_contract_create/', modal_contract_create, name='modal_contract_create'),
    path('save_contract/', save_contract, name='save_contract'),
    path('modal_update_contract/', modal_update_contract, name='modal_update_contract'),

    # ASIGNAR ALMACEN
    path('assign_store_modal/', assign_store_modal, name='assign_store_modal'),

    # BILL
    path('bill/', login_required(bill_list), name='bill_list'),
    path('get_purchase_detail/', login_required(get_purchase_detail), name='get_purchase_detail'),
    path('get_purchases_by_client/', login_required(get_purchases_by_client), name='get_purchases_by_client'),
    # path('save_bill/', login_required(save_bill), name='save_bill'),
    path('print_pdf_bill/<int:pk>/', print_pdf_bill, name='print_pdf_bill'),

    # GET CLIENT
    path('get_client/', login_required(get_client), name='get_client'),

    # GUIDE
    path('modal_new_guide/', login_required(modal_new_guide), name='modal_new_guide'),

    # CONTRACT BUYS
    path('get_buys_by_contract/', login_required(get_buys_by_contract), name='get_buys_by_contract'),

]
