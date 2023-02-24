from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.comercial.views import *
from apps.comercial.views_PDF import guide_print, print_programming_guide, get_input_note, get_output_note, print_ticket

urlpatterns = [
    path('', login_required(Index.as_view()), name='index'),
    path('truck_list/', login_required(TruckList.as_view()), name='truck_list'),
    path('truck_create/', login_required(TruckCreate.as_view()), name='truck_create'),
    path('truck_update/<int:pk>/', login_required(TruckUpdate.as_view()), name='truck_update'),
    path('towing_list/', login_required(TowingList.as_view()), name='towing_list'),
    path('towing_create/', login_required(TowingCreate.as_view()), name='towing_create'),
    path('towing_update/<int:pk>/', login_required(TowingUpdate.as_view()), name='towing_update'),
    path('programming_list/', login_required(ProgrammingList.as_view()), name='programming_list'),
    path('programming_create/', login_required(ProgrammingCreate.as_view()), name='programming_create'),
    path('new_programming/', new_programming, name='new_programming'),
    path('new_guide/', new_guide, name='new_guide'),
    path('get_programming_guide/', get_programming_guide, name='get_programming_guide'),
    path('get_programming/', get_programming, name='get_programming'),
    path('update_programming/', update_programming, name='update_programming'),
    path('get_quantity_product/', get_quantity_product, name='get_quantity_product'),
    path('create_guide/', create_guide, name='create_guide'),
    path('guide_detail_list/', guide_detail_list, name='guide_detail_list'),
    path('guide_by_programming/', guide_by_programming, name='guide_by_programming'),
    path('programmings_by_date/', programmings_by_date, name='programmings_by_date'),
    path('programming_receive_by_sucursal/', programming_receive_by_sucursal,
         name='programming_receive_by_sucursal'),
    path('programming_receive_by_sucursal_detail_guide/', programming_receive_by_sucursal_detail_guide,
         name='programming_receive_by_sucursal_detail_guide'),
    path('get_stock_by_store/', get_stock_by_store, name='get_stock_by_store'),
    path('update_stock_from_programming/', update_stock_from_programming,
         name='update_stock_from_programming'),

    # IO guides
    path('output_guide/', login_required(output_guide), name='output_guide'),
    path('input_guide/', login_required(input_guide), name='input_guide'),
    path('get_products_by_subsidiary_store/', login_required(get_products_by_subsidiary_store),
         name='get_products_by_subsidiary_store'),
    path('create_output_transfer/', login_required(create_output_transfer), name='create_output_transfer'),
    path('create_input_transfer/', login_required(create_input_transfer), name='create_input_transfer'),
    path('output_workflow/', login_required(output_workflow), name='output_workflow'),
    path('input_workflow/', login_required(input_workflow), name='input_workflow'),
    path('input_workflow_from_output/', login_required(input_workflow_from_output),
         name='input_workflow_from_output'),
    path('get_merchandise_of_output/', login_required(get_merchandise_of_output),
         name='get_merchandise_of_output'),
    path('new_input_from_output/', login_required(new_input_from_output), name='new_input_from_output'),
    path('output_change_status/', login_required(output_change_status), name='output_change_status'),
    path('get_stock_by_product_type/', get_stock_by_product_type, name='get_stock_by_product_type'),

    # ReportLab
    path('guide_print/', guide_print, name='guide_print'),
    path('print_programming_guide/<int:pk>/<int:guide>/', print_programming_guide, name='print_programming_guide'),
    path('get_input_note/<int:pk>/', get_input_note, name='get_input_note'),
    path('get_output_note/<int:pk>/', get_output_note, name='get_output_note'),
    path('print_ticket/<int:pk>/', print_ticket, name='print_ticket'),

    # DistributionMovil
    path('distribution_movil_list/', distribution_movil_list, name='distribution_movil_list'),
    path('distribution_mobil_save/', distribution_mobil_save, name='distribution_mobil_save'),
    path('output_distribution_list/', output_distribution_list, name='output_distribution_list'),
    path('c_return_distribution_mobil_detail/', c_return_distribution_mobil_detail,
         name='c_return_distribution_mobil_detail'),
    path('get_order_detail_by_client/', get_order_detail_by_client,
         name='get_order_detail_by_client'),
    path('save_recovered_b/', save_recovered_b,
         name='save_recovered_b'),
    path('get_quantity_last_distribution/', get_quantity_last_distribution, name='get_quantity_last_distribution'),
    path('get_details_by_distributions_mobil/', get_details_by_distributions_mobil,
         name='get_details_by_distributions_mobil'),
    path('get_distribution_mobil_return/', get_distribution_mobil_return,
         name='get_distribution_mobil_return'),
    path('get_distribution_mobil_recovered/', get_distribution_mobil_recovered,
         name='get_distribution_mobil_recovered'),
    path('get_units_by_products_distribution_mobil/', get_units_by_products_distribution_mobil,
         name='get_units_by_products_distribution_mobil'),
    path('return_detail_distribution_mobil_store/', return_detail_distribution_mobil_store,
         name='return_detail_distribution_mobil_store'),
    path('get_distribution_list/', get_distribution_list, name='get_distribution_list'),
    path('output_distribution/', output_distribution, name='output_distribution'),
    path('get_distribution_mobil_sales/', get_distribution_mobil_sales,
         name='get_distribution_mobil_sales'),

    # Mantenimient Product
    path('get_mantenimient_product_list/', get_mantenimient_product_list,
         name='get_mantenimient_product_list'),
    path('mantenimient_product/', mantenimient_product, name='mantenimient_product'),
    path('get_units_and_sotck_by_product/', get_units_and_sotck_by_product,
         name='get_units_and_sotck_by_product'),

    # Fuel programming
    path('get_fuel_request_list/', get_fuel_request_list, name='get_fuel_request_list'),
    path('fuel_request/', fuel_request, name='fuel_request'),
    path('get_products_by_supplier/', get_products_by_supplier, name='get_products_by_supplier'),
    path('get_programming_by_license_plate/', get_programming_by_license_plate,
         name='get_programming_by_license_plate'),
    path('save_fuel_programming/', save_fuel_programming, name='save_fuel_programming'),

    # adelanto de balones de los clientes
    path('get_advancement_client/', login_required(get_advancement_client), name='get_advancement_client'),
    path('advancement_client/', login_required(get_advancement_client), name='advancement_client'),
    path('save_advancement_client/', save_advancement_client, name='save_advancement_client'),

    # reports
    path('get_distribution_query/', login_required(get_distribution_query), name='get_distribution_query'),
    path('list_output_distribution/', login_required(get_output_distributions), name='list_output_distribution'),
    path('report_guide_by_plate/', login_required(report_guide_by_plate), name='report_guide_by_plate'),
    path('report_guides_by_plate_grid/', login_required(report_guides_by_plate_grid), name='report_guides_by_plate_grid'),

]
