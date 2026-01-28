from django.urls import path
from django.contrib.auth.decorators import login_required

from apps.sales.views import *
from apps.sales.views_SUNAT import query_dni
from apps.sales.views_PDF import product_print, account_order_list_pdf, \
    pdf_get_orders_for_status_account, print_quotation, print_order_bill, print_sales_report_professional

urlpatterns = [
    path('product_list/', login_required(ProductList.as_view()), name='product_list'),
    path('json_product_create/', login_required(JsonProductCreate.as_view()), name='json_product_create'),
    path('json_product_list/', login_required(JsonProductList.as_view()), name='json_product_list'),
    path('json_product_edit/<int:pk>/',
         login_required(JsonProductUpdate.as_view()), name='json_product_edit'),
    path('get_product/', get_product, name='get_product'),
    path('get_products_ajax/', get_products_ajax, name='get_products_ajax'),
    path('get_supplies_view/', get_supplies_view, name='get_supplies_view'),
    path('new_quantity_on_hand/', new_quantity_on_hand, name='new_quantity_on_hand'),

    path('get_kardex_by_product/', get_kardex_by_product, name='get_kardex_by_product'),
    path('get_list_kardex/', get_list_kardex, name='get_list_kardex'),

    path('client_list/', login_required(ClientList.as_view()), name='client_list'),

    path('new_client/', new_client, name='new_client'),
    path('new_client_associate/', new_client_associate, name='new_client_associate'),

    path('sales_list/', login_required(SalesOrder.as_view()), name='sales_list'),

    path('set_product_detail/', set_product_detail, name='set_product_detail'),
    path('get_product_detail/', get_product_detail, name='get_product_detail'),
    path('update_product_detail/', update_product_detail, name='update_product_detail'),
    path('toogle_status_product_detail/', toogle_status_product_detail,
         name='toogle_status_product_detail'),

    path('get_rate_product/', get_rate_product, name='get_rate_product'),
    path('save_order/', save_order, name='save_order'),
    path('query_dni/', query_dni, name='query_dni'),

    path('generate_invoice/', generate_invoice, name='generate_invoice'),
    path('get_products_by_subsidiary/', get_products_by_subsidiary, name='get_products_by_subsidiary'),
    path('new_subsidiary_store/', new_subsidiary_store, name='new_subsidiary_store'),
    path('get_recipe/', login_required(get_recipe), name='get_recipe'),
    path('get_unit_by_product/', get_unit_by_product, name='get_unit_by_product'),
    path('get_price_by_product/', get_price_by_product, name='get_price_by_product'),

    # product get recipe
    path('get_recipe_by_product/', get_recipe_by_product, name='get_recipe_by_product'),

    # ReportLab
    path('product_print/', product_print, name='product_print'),
    path('product_print/<int:pk>/', product_print, name='product_print_one'),

    # GlP KARDEX

    path('stock_product/', login_required(get_stock_product_store), name='stock_product'),
    path('stock_product_all/', login_required(get_stock_product_store_all), name='stock_product_all'),

    # PDFKIT
    path('account_order_list_pdf/<int:pk>/',
         login_required(account_order_list_pdf), name='account_order_list_pdf'),

    # ESTADO DE CUENTA
    path('order_list/', login_required(order_list), name='order_list'),
    path('get_orders_by_client/', get_orders_by_client, name='get_orders_by_client'),
    path('get_order_detail_for_pay/', get_order_detail_for_pay, name='get_order_detail_for_pay'),
    path('new_loan_payment/', login_required(new_loan_payment), name='new_loan_payment'),
    path('get_expenses/', login_required(get_expenses), name='get_expenses'),
    path('new_expense/', login_required(new_expense), name='new_expense'),

    path('get_recipe_by_product/', get_recipe_by_product, name='get_recipe_by_product'),

    # report graphic
    path('get_report_sales_subsidiary/', login_required(get_report_sales_subsidiary), name='get_report_sales_subsidiary'),

    # report payments
    path('report_payments_by_client/', login_required(report_payments_by_client), name='report_payments_by_client'),

    # check payment
    path('check_loan_payment/', login_required(check_loan_payment), name='check_loan_payment'),

    path('test/', login_required(test), name='test'),
    path('pdf_get_orders_for_status_account/', login_required(pdf_get_orders_for_status_account), name='pdf_get_orders_for_status_account'),

    # purchase_report_by_category
    path('purchase_report_by_category/', login_required(purchase_report_by_category), name='purchase_report_by_category'),

    # QUOTATION
    path('quotation/', login_required(quotation_list), name='quotation_list'),
    path('save_quotation/', login_required(save_quotation), name='save_quotation'),
    path('get_product_quotation/', login_required(get_product_quotation), name='get_product_quotation'),
    path('get_clients_by_criteria/', login_required(get_clients_by_criteria), name='get_clients_by_criteria'),
    path('print_quotation/<int:pk>/<str:t>/', print_quotation, name='print_quotation'),
    path('get_order_by_correlative/', login_required(get_order_by_correlative), name='get_order_by_correlative'),

    # CLIENT
    path('client_save/', login_required(client_save), name='client_save'),
    path('modal_client_create/', login_required(modal_client_create), name='modal_client_create'),
    path('modal_client_update/', login_required(modal_client_update), name='modal_client_update'),
    path('client_update/', login_required(client_update), name='client_update'),
    path('get_api_client/', login_required(get_api_client), name='get_api_client'),
    path('get_departments_ajax/', login_required(get_departments_ajax), name='get_departments_ajax'),
    path('get_provinces_ajax/', login_required(get_provinces_ajax), name='get_provinces_ajax'),
    path('get_districts_ajax/', login_required(get_districts_ajax), name='get_districts_ajax'),

    # Cuentas por cobrar
    path('accounts_receivable_report/', login_required(accounts_receivable_report), name='accounts_receivable_report'),
    path('get_client_payment_modal/', login_required(get_client_payment_modal), name='get_client_payment_modal'),
    path('save_client_payment/', login_required(save_client_payment), name='save_client_payment'),
    path('get_warranty_verification_modal/', login_required(get_warranty_verification_modal), name='get_warranty_verification_modal'),
    path('save_warranty_verification/', login_required(save_warranty_verification), name='save_warranty_verification'),
    path('get_payment_details_modal/', login_required(get_payment_details_modal), name='get_payment_details_modal'),
    path('get_warranty_details_modal/', login_required(get_warranty_details_modal), name='get_warranty_details_modal'),
    path('get_payment_detail_view/', login_required(get_payment_detail_view), name='get_payment_detail_view'),

    # List quotation
    path('get_sales_quotation_by_subsidiary/', login_required(get_sales_quotation_by_subsidiary), name='get_sales_quotation_by_subsidiary'),

    # SALES NEW
    path('get_product_grid/', login_required(get_product_grid), name='get_product_grid'),
    path('check_stock/', login_required(check_stock), name='check_stock'),
    path('print_order_bill/<int:pk>/', print_order_bill, name='print_order_bill'),
    path('get_correlative/', login_required(get_correlative), name='get_correlative'),

    # SALES GUIDE
    path('sales/<int:guide>/', get_sales_list, name='sales'),

    # CREATE_SALE_WAREHOUSE
    path('create_warehouse_sale/', login_required(create_warehouse_sale), name='create_warehouse_sale'),
    path('delete_warehouse_sale/', login_required(delete_warehouse_sale), name='delete_warehouse_sale'),

    # SEARCH SALE
    path('get_order_by_id/', login_required(get_order_by_id), name='get_order_by_id'),
    path('get_name_business/', login_required(get_name_business), name='get_name_business'),

    # LOGISTIC
    path('bills_pending/', login_required(get_purchases_bills), name='bills_pending'),
    path('assign_to_warehouse/', login_required(assign_to_warehouse), name='assign_to_warehouse'),
    path('save_detail_to_warehouse/', login_required(save_detail_to_warehouse), name='save_detail_to_warehouse'),
    path('get_details_by_bill/', login_required(get_details_by_bill), name='get_details_by_bill'),
    path('bills_in_warehouse/', login_required(get_bills_in_warehouse), name='bills_in_warehouse'),
    path('bill_credit_note/', login_required(bill_credit_note), name='bill_credit_note'),
    path('bill_create_credit_note/', login_required(bill_create_credit_note), name='bill_create_credit_note'),
    path('check_batch_number/', login_required(check_batch_number), name='check_batch_number'),

    # KARDEX
    path('kardex/', login_required(kardex_list), name='kardex'),

    # PRODUCTS
    path('get_product_autocomplete/', login_required(get_product_autocomplete), name='get_product_autocomplete'),
    path('get_product_by_id/', login_required(get_product_by_id), name='get_product_by_id'),
    path('modal_batch/', login_required(modal_batch), name='modal_batch'),

    # REPORTE DE VENTAS PROFESIONAL
    path('sales_report_professional/', login_required(sales_report_professional), name='sales_report_professional'),
    path('print_sales_report_professional/', login_required(print_sales_report_professional), name='print_sales_report_professional'),

    # MÓDULO DE PRECIOS
    path('price_management/', login_required(PriceManagementView.as_view()), name='price_management'),
    path('price_type_list/', login_required(PriceTypeList.as_view()), name='price_type_list'),  # Legacy redirect
    path('product_price_list/', login_required(ProductPriceList.as_view()), name='product_price_list'),  # Legacy redirect
    path('price_type_save/', login_required(price_type_save), name='price_type_save'),
    path('price_type_delete/', login_required(price_type_delete), name='price_type_delete'),
    path('product_price_save/', login_required(product_price_save), name='product_price_save'),
    path('product_price_delete/', login_required(product_price_delete), name='product_price_delete'),
    path('get_price_by_client_and_product/', login_required(get_price_by_client_and_product), name='get_price_by_client_and_product'),
    path('get_prices_by_price_type/', login_required(get_prices_by_price_type), name='get_prices_by_price_type'),

]

