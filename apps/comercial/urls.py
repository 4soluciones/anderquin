from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.comercial.views import *
from apps.comercial.views_PDF import guide_print, print_programming_guide, get_input_note, get_output_note, \
    guide, picking, transfer_print

urlpatterns = [
    path('truck_list/', login_required(TruckList.as_view()), name='truck_list'),
    path('truck_create/', login_required(TruckCreate.as_view()), name='truck_create'),
    path('truck_update/<int:pk>/', login_required(TruckUpdate.as_view()), name='truck_update'),
    path('towing_list/', login_required(TowingList.as_view()), name='towing_list'),
    path('towing_create/', login_required(TowingCreate.as_view()), name='towing_create'),
    path('towing_update/<int:pk>/', login_required(TowingUpdate.as_view()), name='towing_update'),
    path('get_quantity_product/', get_quantity_product, name='get_quantity_product'),
    # path('create_guide/', create_guide, name='create_guide'),
    path('guide_detail_list/', guide_detail_list, name='guide_detail_list'),
    path('get_stock_by_store/', get_stock_by_store, name='get_stock_by_store'),

    # Transferencias entre almacenes
    path('transfer_list/', login_required(transfer_list), name='transfer_list'),
    path('transfer_create/', login_required(transfer_create), name='transfer_create'),
    path('transfer_save/', login_required(transfer_save), name='transfer_save'),
    path('get_products_batches_by_store/', login_required(get_products_batches_by_store), name='get_products_batches_by_store'),
    path('get_product_store_price/', login_required(get_product_store_price), name='get_product_store_price'),
    path('transfer_receive_list/', login_required(transfer_receive_list), name='transfer_receive_list'),
    path('transfer_accept/<int:pk>/', login_required(transfer_accept), name='transfer_accept'),
    path('direct_input_warehouse/', login_required(direct_input_warehouse), name='direct_input_warehouse'),

    # IO guides
    path('output_guide/', login_required(output_guide), name='output_guide'),
    path('input_guide/', login_required(input_guide), name='input_guide'),
    path('get_products_by_subsidiary_store/', login_required(get_products_by_subsidiary_store),
         name='get_products_by_subsidiary_store'),
    path('output_workflow/', login_required(output_workflow), name='output_workflow'),
    path('input_workflow/', login_required(input_workflow), name='input_workflow'),
    path('input_workflow_from_output/', login_required(input_workflow_from_output),
         name='input_workflow_from_output'),
    path('get_merchandise_of_output/', login_required(get_merchandise_of_output),
         name='get_merchandise_of_output'),

    # ReportLab
    path('guide_print/', guide_print, name='guide_print'),
    path('print_programming_guide/<int:pk>/<int:guide>/', print_programming_guide, name='print_programming_guide'),
    path('get_input_note/<int:pk>/', get_input_note, name='get_input_note'),
    path('get_output_note/<int:pk>/', get_output_note, name='get_output_note'),
    path('transfer_print/<int:pk>/', login_required(transfer_print), name='transfer_print'),

    # DistributionMovil
    path('distribution_movil_list/', distribution_movil_list, name='distribution_movil_list'),

    path('get_order_detail_by_client/', get_order_detail_by_client,
         name='get_order_detail_by_client'),

    path('get_units_by_products_distribution_mobil/', get_units_by_products_distribution_mobil,
         name='get_units_by_products_distribution_mobil'),
    path('output_distribution/', output_distribution, name='output_distribution'),
    path('get_distribution_mobil_sales/', get_distribution_mobil_sales,
         name='get_distribution_mobil_sales'),

    # Mantenimient Product
    path('get_units_and_sotck_by_product/', get_units_and_sotck_by_product,
         name='get_units_and_sotck_by_product'),

    # Fuel programming
    path('get_products_by_supplier/', get_products_by_supplier, name='get_products_by_supplier'),

    # reports
    path('list_output_distribution/', login_required(get_output_distributions), name='list_output_distribution'),
    path('report_guide_by_plate/', login_required(report_guide_by_plate), name='report_guide_by_plate'),

    # NEW GUIDE
    path('get_guide', login_required(new_guide), name='new_guide'),
    path('new_guide/<int:contract_detail>/', new_guide, name='new_guide'),
    path('modal_guide_origin/', modal_guide_origin, name='modal_guide_origin'),
    path('save_new_address_origin/', save_new_address_origin, name='save_new_address_origin'),
    path('modal_guide_destiny/', modal_guide_destiny, name='modal_guide_destiny'),
    path('save_new_address_client/', save_new_address_client, name='save_new_address_client'),
    path('modal_guide_carrier/', modal_guide_carrier, name='modal_guide_carrier'),
    path('get_vehicle_by_carrier/', get_vehicle_by_carrier, name='get_vehicle_by_carrier'),
    path('get_plate_by_vehicle/', get_plate_by_vehicle, name='get_plate_by_vehicle'),
    path('save_guide/', save_guide, name='save_guide'),
    path('guide/<int:pk>/', login_required(guide), name='guide'),
    path('get_guide_by_contract/', get_guide_by_contract, name='get_guide_by_contract'),
    path('modal_batch_guide/', modal_batch_guide, name='modal_batch_guide'),

    # CREATE CARRIER
    path('modal_new_carrier/', modal_new_carrier, name='modal_new_carrier'),
    path('create_carrier/', create_carrier, name='create_carrier'),
    path('get_carrier_api/', get_carrier_api, name='get_carrier_api'),
    path('get_truck/', get_truck, name='get_truck'),

    # CREATE DRIVER
    path('modal_new_driver/', modal_new_driver, name='modal_new_driver'),
    path('create_driver/', create_driver, name='create_driver'),
    path('new_pilot_associate/', new_pilot_associate, name='new_pilot_associate'),

    # CREATE STORES
    path('get_store/', get_store, name='get_store'),
    path('new_store/', new_store, name='new_store'),

    # GUIDE LIST
    path('guide_list/', guide_list, name='guide_list'),
    path('modal_picking_create/', modal_picking_create, name='modal_picking_create'),
    path('modal_phase/', modal_phase, name='modal_phase'),
    path('save_phase/', save_phase, name='save_phase'),
    path('save_picking/', save_picking, name='save_picking'),
    path('get_picking_with_guide/', get_picking_with_guide, name='get_picking_with_guide'),
    path('get_guide/', get_guide, name='get_guide'),
    path('picking/<int:pk>/', picking, name='picking'),

]
