from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.vetstore.views import *
from apps.vetstore.viewsets import *
# from . import views, viewsets
urlpatterns = [

    path('', login_required(Home.as_view()), name='home'),

    path('get_page/', get_page, name='get_page'),
    path('get_criteria_product/', get_criteria_product, name='get_criteria_product'),

    # form administrator
    path('get_product/', get_product, name='get_product'),
    path('get_supplier/', get_supplier, name='get_supplier'),
    path('get_attendances_list/', get_attendances_list, name='get_attendances_list'),
    path('recalculate_product/', recalculate_product, name='recalculate_product'),

    path('get_sale/', get_sale, name='get_sale'),
    path('get_purchase/', get_purchase, name='get_purchase'),
    path('get_group_payments/', get_group_payments, name='get_group_payments'),
    path('go_back_brand/', go_back_brand, name='go_back_brand'),

    # registration form
    path('product_registration/', product_registration, name='product_registration'),
    path('supplier_registration/', supplier_registration, name='supplier_registration'),
    path('attendance_registration/', attendance_registration, name='attendance_registration'),
    path('expense_registration/', expense_registration, name='expense_registration'),
    path('branch_registration/', branch_registration, name='branch_registration'),

    path('add_category/', add_category, name='add_category'),

    path('generate_purchase_receipt/', generate_purchase_receipt, name='generate_purchase_receipt'),
    path('generate_sales_receipt/', generate_sales_receipt, name='generate_sales_receipt'),
    path('generate_product_return_receipt/', generate_product_return_receipt,
         name='generate_product_return_receipt'),

    # update form
    path('product_update/', product_update, name='product_update'),
    path('supplier_update/', supplier_update, name='supplier_update'),
    path('brand_update/', brand_update, name='brand_update'),
    path('update_category/', update_category, name='update_category'),
    path('update_employee/', update_employee, name='update_employee'),

    # delete form
    path('delete_category/', delete_category, name='delete_category'),

    # desplegables
    path('rest/get_brand/', get_brand),
    path('rest/get_category/', get_category),
    path('rest/get_branch_office/', get_branch_office),
    path('rest/get_employee/', get_employee),

    # auto-completable lists
    path('category_list/', category_list),
    path('supplier_list/', supplier_list),
    path('purchase_product_autocomplete_list/', purchase_product_autocomplete_list),
    path('sale_product_autocomplete_list/', sale_product_autocomplete_list),
    path('product_return_product_autocomplete_list/', product_return_product_autocomplete_list),

    # choices
    path('way_pay/', way_pay, name='way_pay'),
    path('product_return_type/', product_return_type, name='product_return_type'),

    # Export data to excel
    path('export_users_csv/', export_users_csv, name='export_users_csv'),
    path('export_products_csv/', export_products_csv, name='export_products_csv'),
    path('export_batches_csv/', export_batches_csv, name='export_batches_csv'),

]
