from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models.functions import Coalesce
from django.shortcuts import render
import decimal
import json
from datetime import datetime
from http import HTTPStatus

from django.contrib.auth.models import User
from django.core import serializers
from django.db.models import Q, Sum, F, Prefetch, Subquery, OuterRef, Max
from django.http import JsonResponse
from django.shortcuts import render
from django.template import loader
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from apps.hrm.models import Subsidiary
from apps.hrm.views import get_subsidiary_by_user
from apps.sales.views import kardex_input, kardex_ouput, kardex_initial, calculate_minimum_unit, \
    save_loan_payment_in_cash_flow, Client, ClientAddress, ClientType, ClientAssociate
from .models import *
from .views_PDF import query_apis_net_money
from ..accounting.models import BillPurchase, Bill
from ..comercial.models import GuideMotive
from ..sales.models import Product, Unit, Supplier, SubsidiaryStore, ProductStore, ProductDetail, Kardex, Cash, \
    CashFlow, TransactionPayment, SupplierAddress, Order, SupplierAccounts
from ..sales.views_SUNAT import query_apis_net_dni_ruc


# class Home(TemplateView):
# template_name = 'buys/home.html'

def get_correlative_by_year(request):
    if request.method == 'GET':
        year = request.GET.get('year', '')
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        correlative = get_correlative_by_subsidiary(subsidiary_obj, year)

        return JsonResponse({
            'correlative': str(correlative).zfill(4),
        }, status=HTTPStatus.OK)


def get_correlative_by_subsidiary(subsidiary_obj=None, year=None):
    # number = Purchase.objects.filter(subsidiary=subsidiary_obj).aggregate(
    #     r=Coalesce(Max('correlative'), 0)).get('r')
    # return number + 1

    search = Purchase.objects.filter(year=year, status__in=['S', 'A'], bill_number__isnull=False)
    if search.exists():
        purchase_obj = search.last()
        correlative = purchase_obj.correlative
        if correlative:
            new_correlative = correlative + 1
            result = new_correlative
        else:
            result = 1
    else:
        result = 1

    return result


def save_purchase(request):
    if request.method == 'GET':
        purchase_request = request.GET.get('purchase', '')
        # print(purchase_request)
        data_purchase = json.loads(purchase_request)
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")

        supplier_id = str(data_purchase["SupplierId"])
        reference = str(data_purchase["Reference"])
        date_delivery = str(data_purchase["Date"])
        if str(data_purchase["Delivery_date"]):
            date_delivery = str(data_purchase["Delivery_date"])
        # print(date_delivery)
        type_pay = str(data_purchase["Type_Pay"])
        pay_condition = str(data_purchase["Pay_condition"])
        base_total = decimal.Decimal(data_purchase["Base_Total"])
        igv_total = decimal.Decimal(data_purchase["Igv_Total"])
        total = decimal.Decimal(data_purchase["Import_Total"])
        check_igv = str(data_purchase["Check_Igv"])
        check_dollar = str(data_purchase["Check_Dollar"])

        client_reference = int(data_purchase["client_reference_id"])
        client_entity = data_purchase["client_final"]

        check_subsidiary = str(data_purchase["check-subsidiary"])
        check_provider = str(data_purchase["check-provider"])
        check_client_reference = str(data_purchase["check-client"])
        check_client_entity = str(data_purchase["check-client-final"])

        address_subsidiary = data_purchase["address_subsidiary"]
        address_provider = data_purchase["address_provider"]
        client_address_reference = data_purchase["client_address_reference"]
        client_address_entity = data_purchase["client_final_address"]

        observations = str(data_purchase["observations"])
        date = str(data_purchase["Date"])

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        supplier_obj = Supplier.objects.get(id=int(supplier_id))

        currency_type = 'S'
        if check_dollar == '1':
            currency_type = 'D'

        client_reference_obj = None
        delivery_choice = ''
        city = ''

        if client_reference:
            client_reference_obj = Client.objects.get(id=int(client_reference))
        client_entity_obj = None
        if client_entity:
            client_entity_obj = Client.objects.get(id=int(client_entity))
        delivery_address = ''
        subsidiary_address_obj = None
        address_provider_obj = None
        client_address_obj = None

        if check_subsidiary == '1':
            subsidiary_address_obj = Subsidiary.objects.get(id=int(address_subsidiary))
            delivery_address = subsidiary_address_obj.address
            delivery_choice = 'S'
            city = subsidiary_address_obj.district.description
        elif check_provider == '1':
            address_provider_set = SupplierAddress.objects.filter(id=int(address_provider))
            delivery_choice = 'P'
            if address_provider_set.exists():
                address_provider_obj = address_provider_set.last()
                delivery_address = address_provider_obj.address
                city = address_provider_obj.district.description

        elif check_client_reference == '1':
            client_address_referencer_set = ClientAddress.objects.filter(id=int(client_address_reference))
            delivery_choice = 'CR'
            if client_address_referencer_set.exists():
                client_address_obj = client_address_referencer_set.last()
                delivery_address = client_address_obj.address
                city = client_address_obj.district.description

        elif check_client_entity == '1':
            client_address_entity_set = ClientAddress.objects.filter(id=int(client_address_entity))
            delivery_choice = 'CP'
            if client_address_entity_set.exists():
                client_address_obj = client_address_entity_set.last()
                delivery_address = client_address_obj.address
                city = client_address_obj.district.description

        correlative = int(data_purchase["correlative"])

        _bill_number = f'OC-{datetime.now().year}-{str(correlative).zfill(4)}'

        purchase_obj = Purchase(
            supplier=supplier_obj,
            purchase_date=date,
            user=user_obj,
            subsidiary=subsidiary_obj,
            bill_number=_bill_number,
            payment_method=type_pay,
            payment_condition=pay_condition,
            currency_type=currency_type,
            client_reference=client_reference_obj,
            client_reference_entity=client_entity_obj,
            delivery_address=delivery_address.upper(),
            delivery_choice=delivery_choice,
            observation=observations.upper(),
            city=city.upper(),
            # contract_detail=contract_detail_obj,
            delivery_date=date_delivery,
            correlative=correlative,
            reference=reference,
            delivery_subsidiary=subsidiary_address_obj,
            delivery_supplier=address_provider_obj,
            delivery_client=client_address_obj,
            year='2024'
        )
        purchase_obj.save()

        for detail in data_purchase['Details']:
            quantity = decimal.Decimal(detail['Quantity'])
            quantity_units = decimal.Decimal(detail['QuantityUnits'])
            price = decimal.Decimal(detail['Price'])
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)

            new_purchase_detail = {
                'purchase': purchase_obj,
                'product': product_obj,
                'quantity': quantity_units,
                'unit': unit_obj,
                'price_unit': price,
            }
            new_purchase_detail_obj = PurchaseDetail.objects.create(**new_purchase_detail)
            new_purchase_detail_obj.save()
        contract = False
        if data_purchase["contract_detail_id"]:
            contract = True
            contract_detail_array = data_purchase["contract_detail_id"].split(',')
            for c in contract_detail_array:
                contract_detail_obj = ContractDetail.objects.get(id=int(c))
                ContractDetailPurchase.objects.create(contract_detail=contract_detail_obj, purchase=purchase_obj)

        return JsonResponse({
            'pk': purchase_obj.id,
            'message': 'Orden Registrada Correctamante.',
            'contract': contract
        }, status=HTTPStatus.OK)


def save_detail_buy_order_store(request):
    if request.method == 'GET':
        purchase_request = request.GET.get('details', '')
        data_purchase = json.loads(purchase_request)

        assign_date = str(data_purchase["AssignDate"])
        purchase_id = int(data_purchase["Purchase"])
        purchase_obj = Purchase.objects.get(id=int(purchase_id))

        batch_number = data_purchase["Batch"]
        batch_expiration_date = str(data_purchase["BatchExpirationDate"])
        guide_number = data_purchase["GuideNumber"]
        store = data_purchase["Store"]

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(store))

        purchase_store_obj = Purchase(
            purchase_date=purchase_obj.purchase_date,
            status='A',
            subsidiary=purchase_obj.subsidiary,
            supplier=purchase_obj.supplier,
            user=user_obj,
            client_reference=None,
            client_reference_id=None,
            assign_date=assign_date,
            batch_expiration_date=batch_expiration_date,
            batch_number=batch_number,
            guide_number=guide_number,
            year=purchase_obj.year,
            bill_status=purchase_obj.bill_status,
            store_destiny=subsidiary_store_obj,
            parent_purchase=purchase_obj,
        )
        purchase_store_obj.save()

        for d in data_purchase['Details']:

            # purchase_detail = int(d['PurchaseDetail'])
            # purchase_detail_obj = PurchaseDetail.objects.get(id=purchase_detail)

            product_id = int(d['Product'])
            product_obj = Product.objects.get(id=product_id)
            unit_id = int(d['UnitPurchase'])
            unit_obj = Unit.objects.get(id=unit_id)
            unit_min_product = ProductDetail.objects.get(product=product_obj, unit=unit_obj).quantity_minimum

            price_purchase = decimal.Decimal(d['PricePurchase'])
            quantity_purchase = decimal.Decimal(d['QuantityPurchased'])

            try:
                product_store_obj = ProductStore.objects.get(product=product_obj, subsidiary_store=subsidiary_store_obj)
            except ProductStore.DoesNotExist:
                product_store_obj = None

            unit_und_obj = Unit.objects.get(name='UND')

            # ----------------------------------- QUANTITY ENTERED --------------------------------------------------

            entered_quantity_principal = decimal.Decimal(d['EnteredQuantityPrincipal'])
            entered_quantity_in_units = entered_quantity_principal * unit_min_product
            entered_quantity_units = d['EnteredQuantityUnits']

            if entered_quantity_principal != 0 and entered_quantity_principal != '':
                detail_entered_obj = PurchaseDetail.objects.create(quantity=entered_quantity_principal, unit=unit_obj,
                                                                   price_unit=price_purchase, product=product_obj,
                                                                   status_quantity='I', purchase=purchase_store_obj)
                if product_store_obj is None:
                    new_product_store_obj = ProductStore(
                        product=product_obj,
                        subsidiary_store=subsidiary_store_obj,
                        stock=entered_quantity_in_units
                    )
                    new_product_store_obj.save()
                    kardex_initial(new_product_store_obj, entered_quantity_in_units, price_purchase)
                else:
                    kardex_input(product_store_obj.id, entered_quantity_in_units, price_purchase)

            if entered_quantity_units != 0 and entered_quantity_units != '':
                detail_entered_units_obj = PurchaseDetail.objects.create(quantity=entered_quantity_units,
                                                                         price_unit=price_purchase, unit=unit_und_obj,
                                                                         product=product_obj, status_quantity='I',
                                                                         purchase=purchase_store_obj)
                if product_store_obj is None:
                    new_product_store_obj = ProductStore(
                        product=product_obj,
                        subsidiary_store=subsidiary_store_obj,
                        stock=entered_quantity_units
                    )
                    new_product_store_obj.save()
                    kardex_initial(new_product_store_obj, entered_quantity_units, price_purchase)
                else:
                    kardex_input(product_store_obj.id, entered_quantity_units, price_purchase)

            # ----------------------------------- QUANTITY RETURNED --------------------------------------------------

            returned_quantity_principal = d['ReturnedQuantityPrincipal']
            returned_quantity_units = d['ReturnedQuantityUnits']

            if returned_quantity_principal != 0 and returned_quantity_principal != '':
                PurchaseDetail.objects.create(quantity=returned_quantity_principal, price_unit=price_purchase,
                                              unit=unit_obj,
                                              product=product_obj, status_quantity='D', purchase=purchase_store_obj)

            if returned_quantity_units != 0 and returned_quantity_units != '':
                PurchaseDetail.objects.create(quantity=returned_quantity_units, price_unit=price_purchase,
                                              unit=unit_und_obj,
                                              product=product_obj, status_quantity='D', purchase=purchase_store_obj)

            # ----------------------------------- QUANTITY SOLD --------------------------------------------------

            sold_quantity_principal = d['SoldQuantityPrincipal']
            sold_quantity_units = d['SoldQuantityUnit']
            sold_order_id = d['SoldOrderId']
            order_sale_obj = None
            if sold_quantity_principal != 0 and sold_quantity_principal != '':
                order_sale_obj = Order.objects.get(id=int(sold_order_id))
                PurchaseDetail.objects.create(quantity=sold_quantity_principal, price_unit=price_purchase,
                                              unit=unit_obj,
                                              product=product_obj, status_quantity='V', purchase=purchase_store_obj,
                                              order=order_sale_obj)

            if sold_quantity_units != 0 and sold_quantity_units != '':
                PurchaseDetail.objects.create(quantity=sold_quantity_units, price_unit=price_purchase,
                                              unit=unit_und_obj,
                                              product=product_obj, status_quantity='V', purchase=purchase_store_obj,
                                              order=order_sale_obj)

        purchase_obj.status = 'A'
        purchase_obj.save()
        return JsonResponse({
            'message': 'PRODUCTO(S) REGISTRADOS',
        }, status=HTTPStatus.OK)


def get_buy_order_list(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        return render(request, 'buys/buy_order_list.html', {
            'subsidiary_obj': subsidiary_obj
        })

    elif request.method == 'POST':
        option = request.POST.get('value')

        status_filter = {
            'T': ['S', 'A', 'N'],
            'S': ['S'],
            'A': ['A'],
            'N': ['N']
        }.get(option, [])

        if status_filter:
            purchase_set = Purchase.objects.filter(bill_number__isnull=False, status__in=status_filter
                                                   ).select_related('supplier', 'subsidiary', 'client_reference',
                                                                    'client_reference_entity', 'delivery_supplier',
                                                                    'delivery_subsidiary', 'delivery_client',
                                                                    'store_destiny', 'user').prefetch_related(
                Prefetch('purchasedetail_set', queryset=PurchaseDetail.objects.select_related('unit', 'product')),
                Prefetch('billpurchase_set', queryset=BillPurchase.objects.select_related('bill'))
            ).order_by('correlative')

            return JsonResponse({
                'grid': get_dict_order_list(purchase_set),
            }, status=HTTPStatus.OK)

        else:
            data = {'error': "Opción no válida"}
            return JsonResponse(data, status=HTTPStatus.BAD_REQUEST)


def get_dict_order_list(purchase_set):
    purchase_dict = []

    for p in purchase_set:
        client_reference_entity = p.client_reference_entity.names if p.client_reference_entity else None
        purchase_parent = ''
        guide_number = '-'
        bill_numbers = []
        parent_purchase_set = Purchase.objects.filter(parent_purchase_id=p.id).select_related('parent_purchase')
        if parent_purchase_set.exists():
            parent_purchase_get = parent_purchase_set.last()
            guide_number = parent_purchase_get.guide_number
            purchase_parent = parent_purchase_get.id

        # for pd in PurchaseDetail.objects.filter(purchase=p):
        #     for bp in BillPurchase.objects.filter(purchase_detail=pd):
        #         item_bp = {
        #             'id': bp.id,
        #             'bill_number': bp.bill.serial + '-' + bp.bill.correlative
        #         }
        #         bill_numbers.append(item_bp)

        item_purchase = {
            'id': p.id,
            'purchase_parent': purchase_parent,
            'purchase_date': p.purchase_date,
            'buy_number': p.bill_number,
            'supplier': p.supplier.name,
            'client_reference': p.client_reference.names,
            'client_entity': client_reference_entity,
            'delivery_address': p.delivery_address,
            'user': p.user.worker_set.last().employee.names,
            'bill_number': p.number_bill(),
            'status_store_text': p.get_status_display,
            'status_store': p.status,
            'status_bill': p.bill_status,
            'guide_number': guide_number,
            'bill_numbers': bill_numbers,
            'refund': p.get_quantity_refund()
        }
        purchase_dict.append(item_purchase)

    tpl = loader.get_template('buys/buy_order_grid_list.html')
    context = ({
        'purchases': purchase_dict
    })
    return tpl.render(context)


def get_buy_order_store_list(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        if pk != '':
            dates_request = request.GET.get('dates', '')
            data_dates = json.loads(dates_request)
            date_initial = (data_dates["date_initial"])
            date_final = (data_dates["date_final"])
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            purchases_store = Purchase.objects.filter(status='A', assign_date__range=(
                date_initial, date_final)).distinct('id')
            # purchases_store_serializers = serializers.serialize('json', purchases_store)
            tpl = loader.get_template('buys/buy_order_store_grid_list.html')
            context = ({
                'purchases_store': purchases_store,
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
            })
            # return tpl.render(context)
            #     # context
            # return JsonResponse({
            #     context
            # }, status=HTTPStatus.OK)
        else:
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            return render(request, 'buys/buy_order_store_list.html', {
                # 'purchases_store': purchases_store,
                'date_now': date_now,
            })


def get_purchase_annular_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    purchases_annular = Purchase.objects.filter(status='N')
    return render(request, 'buys/purchase_annular_list.html', {
        'purchases_annular': purchases_annular
    })


def get_detail_purchase_store(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        purchase_obj = Purchase.objects.get(id=pk)
        purchase_details = PurchaseDetail.objects.filter(purchase=purchase_obj)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_stores = SubsidiaryStore.objects.filter(category='V')

        purchase_details_dict = []
        unit_description = ''
        bill_number = ''

        for pd in purchase_details:
            if not bill_number:
                bill_purchase_set = BillPurchase.objects.filter(purchase_detail_id=int(pd.id))
                if bill_purchase_set.exists():
                    bill_purchase_obj = bill_purchase_set.first()
                    serial = bill_purchase_obj.bill.serial
                    correlative = bill_purchase_obj.bill.correlative
                    bill_number = serial + '-' + correlative
            product_detail_get = ProductDetail.objects.filter(unit=pd.unit, product=pd.product).last()
            quantity_minimum = product_detail_get.quantity_minimum
            quantity_in_units = pd.quantity * quantity_minimum
            unit_description = pd.unit.description
            item = {
                'id': pd.id,
                'product_id': pd.product.id,
                'product_name': pd.product.name,
                'quantity': pd.quantity,
                'quantity_in_units': str(round(quantity_in_units, 2)),
                'quantity_minimum': str(quantity_minimum),
                'unit_id': pd.unit.id,
                'unit_name': pd.unit.name,
                'unit_description': pd.unit.description,
                'price_unit': str(round(pd.price_unit, 6)),
                'amount': pd.multiplicate(),
                'units_sold': []
            }
            for u in ProductDetail.objects.filter(product_id=pd.product.id).all():
                item_units = {
                    'id': u.id,
                    'unit_id': u.unit.id,
                    'unit_name': u.unit.name,
                    'unit_description': u.unit.description,
                    'quantity_minimum': round(u.quantity_minimum, 0),
                    'price_purchase': str(round(u.price_purchase, 6))
                }
                item.get('units_sold').append(item_units)
            purchase_details_dict.append(item)

        t = loader.get_template('buys/assignment_detail_buy_order.html')
        c = ({
            'formatdate': formatdate,
            'purchase': purchase_obj,
            # 'detail_purchase': purchase_details,
            'detail_purchase': purchase_details_dict,
            'unit_name': unit_description,
            'subsidiary_stores': subsidiary_stores,
            'bill_number': bill_number,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def get_quantity_minimum(request):
    if request.method == 'GET':
        product_id = request.GET.get('product_id', '')
        unit_id = request.GET.get('unit_id', '')
        product_detail_set = ProductDetail.objects.filter(product__id=product_id, unit__id=unit_id)
        if product_detail_set.exists():
            product_detail_obj = product_detail_set.last()
            quantity_minimum = product_detail_obj.quantity_minimum
            price_sale = product_detail_obj.price_sale
            price_purchase = product_detail_obj.price_purchase
            unit_name = product_detail_obj.unit.name
            unit_description = product_detail_obj.unit.description

            return JsonResponse({
                'quantity_minimum': round(quantity_minimum, 0),
                'price_sale': price_sale,
                'price_purchase': price_purchase,
                'unit_name': unit_name,
                'unit_description': unit_description
            }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'message': 'No existe unidades'
            }, status=HTTPStatus.OK)


def get_units_product(request):
    id_product = request.GET.get('ip', '')
    product_obj = Product.objects.get(pk=int(id_product))
    product_obj = Product.objects.get(pk=int(id_product))
    units = Unit.objects.filter(productdetail__product=product_obj)
    units_serialized_obj = serializers.serialize('json', units)

    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    product_store_obj = ProductStore.objects.filter(product_id=id_product,
                                                    subsidiary_store__subsidiary=subsidiary_obj,
                                                    subsidiary_store__category='V').first()
    return JsonResponse({
        'units': units_serialized_obj,
        'stock': product_store_obj.stock,
    }, status=HTTPStatus.OK)


def update_state_annular_purchase(request):
    if request.method == 'GET':
        id_purchase = request.GET.get('pk', '')
        purchase_obj = Purchase.objects.get(pk=int(id_purchase))
        contract_detail_purchase = ContractDetailPurchase.objects.filter(purchase=purchase_obj)
        contract_detail_purchase.delete()

        if purchase_obj.status == 'A':
            data = {'error': 'LA COMPRA YA ESTA APROBADA NO ES POSIBLE ANULAR'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        purchase_obj.status = 'N'
        purchase_obj.save()
    return JsonResponse({
        'message': 'COMPRA ANULADA CORRECTAMENTE',

    }, status=HTTPStatus.OK)


def report_purchases_all(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    truck_set = Truck.objects.all().order_by('license_plate')
    truck_set2 = Purchase.objects.filter(subsidiary=subsidiary_obj)
    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        return render(request, 'buys/report_purchases_all.html', {
            'formatdate': formatdate,
            'truck_set': truck_set,
            'truck_set2': truck_set2,
        })

    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        type_document = str(request.POST.get('type-document'))
        purchase_set = ''
        subsidiaries = [1, 2, 3, 4, 6]

        if type_document == 'F':
            purchase_set = Purchase.objects.filter(
                subsidiary__id__in=subsidiaries, purchase_date__range=[start_date, end_date],
                status__in=['S', 'A'], type_bill='F'
            ).select_related('subsidiary').prefetch_related(
                Prefetch(
                    'purchasedetail_set', queryset=PurchaseDetail.objects.select_related('unit', 'product')
                )
            ).select_related('supplier', 'truck').annotate(
                sum_total=Subquery(
                    PurchaseDetail.objects.filter(purchase_id=OuterRef('id')).annotate(
                        return_sum_total=Sum(F('quantity') * F('price_unit'))).values('return_sum_total')[:1]
                )
            ).order_by('purchase_date')

        elif type_document == 'T':
            purchase_set = Purchase.objects.filter(
                subsidiary__id__in=subsidiaries, purchase_date__range=[start_date, end_date],
                status__in=['S', 'A']
            ).select_related('subsidiary').prefetch_related(
                Prefetch(
                    'purchasedetail_set', queryset=PurchaseDetail.objects.select_related('unit', 'product')
                )
            ).select_related('supplier', 'truck').annotate(
                sum_total=Subquery(
                    PurchaseDetail.objects.filter(purchase_id=OuterRef('id')).annotate(
                        return_sum_total=Sum(F('quantity') * F('price_unit'))).values('return_sum_total')[:1]
                )
            ).order_by('purchase_date')

        context = get_all_purchases(purchase_set=purchase_set)

        purchase_dict = context.get('purchase_set')
        sum_all_total = context.get('sum_all_total')
        base_amount = context.get('base_amount')
        truck_dict = context.get('truck_dict')
        igv = context.get('igv')

        tpl = loader.get_template('buys/report_purchases_all_grid.html')
        context = ({
            'truck_dict': truck_dict,
            'purchase_set': purchase_dict,
            'sum_all_total': sum_all_total,
            'base_amount': base_amount,
            'igv': igv,
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_all_purchases(purchase_set):
    sum_all_total = 0
    purchase_dict = []
    truck_dict = {}

    for p in purchase_set.all():

        license_plate = ''
        if p.truck is not None:
            license_plate = p.truck.license_plate
            truck_dict[p.truck.id] = license_plate

        base_amount = float(p.sum_total) / float(1.18)
        igv = float(p.sum_total) - float(base_amount)
        item_purchase = {
            'id': p.id,
            'supplier': p.supplier.name,
            'purchase_date': p.purchase_date,
            'type_bill': p.get_type_bill_display(),
            'bill_number': p.bill_number,
            'status': p.get_status_display(),
            'truck': license_plate,
            'purchase_detail_set': [],
            'purchase_detail_count': p.purchasedetail_set.count(),
            'base_amount': round(float(base_amount), 2),
            'igv': round(float(igv), 2),
            'sum_total': round(float(p.sum_total), 2),
            'subtotal': 0,
            'subsidiary': p.subsidiary.name
        }
        sum_all_total += p.sum_total
        subtotal = 0
        for pd in p.purchasedetail_set.all():
            item_purchases_detail = {
                'id': pd.product.name,
                'product': pd.product.name,
                'quantity': str(pd.quantity),
                'unit': pd.unit.name,
                'price_unit': round(float(pd.price_unit), 2),
            }
            subtotal += pd.quantity * pd.price_unit

            item_purchase.get('purchase_detail_set').append(item_purchases_detail)
        item_purchase['subtotal'] = round(float(subtotal), 2)

        purchase_dict.append(item_purchase)

    base_amount = float(sum_all_total) / 1.18
    igv = float(sum_all_total) - base_amount

    context = ({
        'purchase_set': purchase_dict,
        'truck_dict': truck_dict,
        'sum_all_total': '{:,}'.format(round(float(sum_all_total), 2)),
        'base_amount': '{:,}'.format(round(float(base_amount), 2)),
        'igv': '{:,}'.format(round(float(igv), 2)),
    })

    return context


def report_purchases_by_supplier(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        return render(request, 'buys/report_purchases_by_supplier.html', {
            'formatdate': formatdate,
        })
    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        purchase_dict = []
        sum_total = 0

        purchase_detail_set = PurchaseDetail.objects.filter(
            purchase__status='A', purchase__purchase_date__range=[start_date, end_date]).values(
            'purchase__supplier__name',
            'purchase__supplier__business_name',
            'purchase__supplier__sector',
            'purchase__supplier__id').exclude(purchase__supplier__id__in=[1, 363, 364, 369]).annotate(
            total=Sum(F('price_unit') * F('quantity'))).order_by('-total')

        for p in purchase_detail_set:
            supplier_id = p['purchase__supplier__id']
            supplier_name = p['purchase__supplier__name']
            business_name = p['purchase__supplier__business_name']

            sector_dict = {
                'N': 'NO ESPECIFICA',
                'L': 'NO LLANTAS',
                'P': 'PINTURA',
                'PR': 'PRECINTO',
                'R': 'REPUESTO',
                'C': 'COMBUSTIBLE',
                'G': 'GLP',
                'S': 'SEGUROS',
                'SU': 'SUNAT',
                'LU': 'LUBRICANTES',
                'LA': 'LAVADO',
                'M': 'MANTENIMIENTO',
                'PE': 'PEAJES',
                'O': 'OTROS',
            }

            # x = np.where(ar-r == 4)

            # print(x)
            # print(sector_dict)
            # print(sector_dict['N'])

            category_name = sector_dict[p['purchase__supplier__sector']]
            total = round(decimal.Decimal(p['total']), 2)
            item_purchase = {
                'supplier_id': supplier_id,
                'supplier_name': supplier_name,
                'business_name': business_name,
                'category_name': category_name,
                'total': '{:,}'.format(total)
            }
            purchase_dict.append(item_purchase)

            sum_total += total

        tpl = loader.get_template('buys/report_purchases_by_supplier_grid.html')
        context = ({
            'purchase_dict': purchase_dict,
            'sum_total': '{:,}'.format(round(decimal.Decimal(sum_total), 2)),
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_purchases_by_provider_category(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        return render(request, 'buys/report_purchases_by_provider_category.html', {
            'formatdate': formatdate,
            'category_set': Supplier._meta.get_field('sector').choices,
        })

    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        category_id = str(request.POST.get('category'))
        purchase_dict = []
        sum_total = 0
        purchase_detail_set = PurchaseDetail.objects.filter(purchase__subsidiary__id=subsidiary_obj.id,
                                                            purchase__supplier__sector=category_id,
                                                            purchase__status='A',
                                                            purchase__purchase_date__range=[start_date,
                                                                                            end_date]).values(
            'purchase__supplier__id', 'purchase__supplier__name', 'purchase__supplier__business_name').exclude(
            purchase__supplier__id__in=[1, 363, 364, 369]).annotate(
            total=Sum(F('price_unit') * F('quantity'))).order_by('-total')

        for p in purchase_detail_set:
            supplier_id = p['purchase__supplier__id']
            supplier_name = p['purchase__supplier__name']
            business_name = p['purchase__supplier__business_name']
            total = round(decimal.Decimal(p['total']), 2)
            item_purchase = {
                'supplier_id': supplier_id,
                'supplier_name': supplier_name,
                'business_name': business_name,
                'total': '{:,}'.format(total)
            }
            purchase_dict.append(item_purchase)

            sum_total += total

        tpl = loader.get_template('buys/report_purchases_by_provider_category_grid.html')
        context = ({
            'purchase_dict': purchase_dict,
            'sum_total': '{:,}'.format(round(decimal.Decimal(sum_total), 2)),
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_buy_list(request, contract_detail=None):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    contract_detail_obj = None
    contract_detail_item_set = None
    contract_dict = []
    client = []
    if contract_detail is not None:
        contract_detail_obj = ContractDetail.objects.get(id=int(contract_detail))
        contract_detail_item_set = ContractDetailItem.objects.filter(contract_detail__id=contract_detail)
        client_reference_set = Client.objects.filter(id=contract_detail_obj.contract.client.id)

        for c in client_reference_set:
            client_address_set = c.clientaddress_set.all()
            if client_address_set.exists():
                address_dict = [{
                    'id': cd.id,
                    'address': cd.address,
                    'district': cd.district.description,
                } for cd in client_address_set]
            else:
                address_dict = []

            client.append({
                'id': c.id,
                'names': c.names,
                'type_client_display': c.get_type_client_display(),
                'type_client': c.type_client,
                'number': c.clienttype_set.last().document_number,
                'address': address_dict
            })

        for counter, d in enumerate(contract_detail_item_set, start=1):
            item_contract = {
                'contract_detail_id': d.contract_detail.id,
                'id': d.id,
                'product_id': d.product.id,
                'product_name': d.product.name,
                'product_brand': d.product.product_brand.name,
                'quantity': d.quantity,
                'counter': counter,
                'units': []
            }
            # for u in Unit.objects.filter(productdetail__product__id=d.product.id).all():
            for pd in ProductDetail.objects.filter(product_id=d.product.id).all():
                item_units = {
                    'id': pd.id,
                    'unit_id': pd.unit.id,
                    'unit_name': pd.unit.name,
                    'quantity_minimum': round(pd.quantity_minimum, 0),
                }
                item_contract.get('units').append(item_units)
            contract_dict.append(item_contract)
    supplier_obj = Supplier.objects.all()
    product_obj = Product.objects.all()
    # unitmeasurement_obj = Unit.objects.all()
    my_date = datetime.now()
    formatdate = my_date.strftime("%Y-%m-%d")
    year = my_date.strftime("%Y")
    correlative = get_correlative_by_subsidiary(subsidiary_obj, year)
    return render(request, 'buys/buy_list.html', {
        'supplier_obj': supplier_obj,
        # 'unitmeasurement_obj': unitmeasurement_obj,
        'product_obj': product_obj,
        # 'choices_payments': TransactionPayment._meta.get_field('type').choices,
        'choices_payments_purchase': Purchase._meta.get_field('payment_method').choices,
        'formatdate': formatdate,
        'supplier_set': Supplier.objects.all(),
        'client_set': Client.objects.all(),
        'subsidiary_set': Subsidiary.objects.all().order_by('id'),
        'contract_detail_obj': contract_detail_obj,
        'client': json.dumps(client),
        'contract_detail_item_set': contract_detail_item_set,
        'contract_dict': contract_dict,
        'correlative': str(correlative).zfill(4)
    })


def get_buys_by_contract(request):
    if request.method == 'GET':
        selected_data = json.loads(request.GET.get('selectedData', '[]'))
        selected_data_list = []

        for product_id, data in selected_data.items():
            product_obj = Product.objects.get(id=product_id)
            units = []

            for pd in ProductDetail.objects.filter(product_id=product_id):
                unit_data = {
                    'id': pd.id,
                    'unit_id': pd.unit.id,
                    'unit_name': pd.unit.name,
                    'quantity_minimum': round(pd.quantity_minimum, 0),
                }
                units.append(unit_data)

            contract_detail_ids = data['contractDetailIDs']
            contract_details = ContractDetail.objects.filter(id__in=contract_detail_ids)
            contract_obj = contract_details.first().contract
            contract_data = []
            for c in contract_details:
                item_contract_detail = {
                    'contract_detail_id': c.id,
                    'nro_quota': c.nro_quota,
                    'date': c.date,
                }
                contract_data.append(item_contract_detail)

            client_data = []
            client_reference_set = Client.objects.filter(id=contract_obj.client.id)
            for c in client_reference_set:
                client_address_set = c.clientaddress_set.all()
                if client_address_set.exists():
                    address_dict = [{
                        'id': cd.id,
                        'address': cd.address,
                        'district': cd.district.description,
                    } for cd in client_address_set]
                else:
                    address_dict = []

                client_data.append({
                    'id': c.id,
                    'names': c.names,
                    'type_client_display': c.get_type_client_display(),
                    'type_client': c.type_client,
                    'number': c.clienttype_set.last().document_number,
                    'address': address_dict
                })

            item = {
                'product_id': product_id,
                'product_name': product_obj.name,
                'quantity': data['quantity'],
                # 'contract_detail': contract_detail_ids,
                'contract_id': contract_obj.id,
                'contract_number': contract_obj.contract_number,
                'client_data': client_data,
                'contract_data': contract_data,
                'units': units
            }

            selected_data_list.append(item)
        json_data = json.dumps(selected_data_list, cls=DjangoJSONEncoder)

        return JsonResponse({'redirect_url': f'/buys/buy_list?selected_data={json_data}'})


def get_address_by_supplier_id(request):
    if request.method == 'GET':
        supplier_id = request.GET.get('supplier_id', '')
        supplier_obj = Supplier.objects.get(id=int(supplier_id))
        supplier_address_set = SupplierAddress.objects.filter(supplier=supplier_obj)
        return JsonResponse({
            'supplier_address_set': serializers.serialize('json', supplier_address_set),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_address_by_client_id(request):
    if request.method == 'GET':
        client_id = request.GET.get('client_id', '')
        client_obj = Client.objects.get(id=int(client_id))
        client_address_set = ClientAddress.objects.filter(client=client_obj)
        return JsonResponse({
            'client_address_set': serializers.serialize('json', client_address_set),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_product_by_criteria_table(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
        value = request.GET.get('value', '')
        array_value = value.split()
        product_query = Product.objects
        full_query = None
        product_list = []

        for i in range(0, len(array_value)):
            q = Q(name__icontains=array_value[i]) | Q(product_brand__name__icontains=array_value[i])
            if full_query is None:
                full_query = q
            else:
                full_query = full_query & q

        product_set = product_query.filter(full_query, is_enabled=True).select_related(
            'product_family', 'product_brand').order_by('id')

        if not product_set:
            data = {'error': 'NO EXISTE EL PRODUCTO, FAVOR DE INGRESAR PRODUCTO EXISTENTE.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for e in product_set:
            unit_id = ''
            unit_name = ''
            price_sale = ''
            stock = 0
            product_store_id = ''
            product_store_set = ProductStore.objects.filter(product_id=e.id, subsidiary_store=subsidiary_store_obj)

            if product_store_set.exists():
                product_store_obj = product_store_set.first()
                stock = product_store_obj.stock
                product_store_id = product_store_obj.id

            item_product_list = {
                'id': e.id,
                'name': e.name,
                'brand': e.product_brand.name,
                'unit_dict': [],
                'stock': stock,
                'product_store_id': product_store_id
            }
            if e.productdetail_set.exists():
                for pd in e.productdetail_set.all():
                    item_unit = {
                        'unit_id': pd.unit.id,
                        'unit_name': pd.unit.name,
                        'price_sale': pd.price_sale,
                        'price_purchase': pd.price_purchase,
                        'quantity_minimum': pd.quantity_minimum
                    }
                    item_product_list.get('unit_dict').append(item_unit)
            product_list.append(item_product_list)

        return JsonResponse({
            'productList': product_list,
        }, status=HTTPStatus.OK)


def get_type_change(request):
    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        money_change_set = MoneyChange.objects.filter(search_date=formatdate)

        if money_change_set.exists():
            money_change_obj = money_change_set.first()
            sell = money_change_obj.sell
            buy = money_change_obj.buy

            return JsonResponse({'sell': sell, 'buy': buy},
                                status=HTTPStatus.OK)
        else:
            r = query_apis_net_money(formatdate)

            if r.get('fecha_busqueda') == formatdate:
                sell = round(r.get('venta'), 3)
                buy = round(r.get('compra'), 3)
                search_date = r.get('fecha_busqueda')
                sunat_date = r.get('fecha_sunat')

                money_change_obj = MoneyChange(
                    search_date=search_date,
                    sunat_date=sunat_date,
                    sell=sell,
                    buy=buy
                )
                money_change_obj.save()

            else:
                data = {'error': 'NO SE OBTUVO TIPO DE CAMBIO, ACTUALICE E INTENTE DE NUEVO'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        return JsonResponse({'sell': sell, 'buy': buy},
                            status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_provider(request):
    t = loader.get_template('buys/buy_modal_provider.html')
    c = ({})
    return JsonResponse({
        'form': t.render(c, request),
    })


def get_sunat(request):
    if request.method == 'GET':
        nro_document = request.GET.get('nro_document', '')
        type_document = str(request.GET.get('type', ''))
        person_obj_search = Supplier.objects.filter(ruc=nro_document)
        if person_obj_search.exists():
            names = person_obj_search.last().business_name
            data = {
                'error': 'EL PROVEEDOR ' + str(names) + ' YA SE ENCUENTRA REGISTRADO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        else:
            if type_document == '01':
                type_name = 'DNI'
                r = query_apis_net_dni_ruc(nro_document, type_name)

                if r.get('numeroDocumento') == nro_document:
                    paternal_name = r.get('apellidoPaterno')
                    maternal_name = r.get('apellidoMaterno')
                    nombres = r.get('nombres')
                    result = nombres + ' ' + paternal_name + ' ' + maternal_name
                    return JsonResponse({'result': result}, status=HTTPStatus.OK)
                else:
                    data = {'error': 'NO EXISTE RUC. REGISTRE MANUAL O CORREGIRLO'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

            elif type_document == '06':
                type_name = 'RUC'
                r = query_apis_net_dni_ruc(nro_document, type_name)

                if r.get('numeroDocumento') == nro_document:
                    business_name = r.get('nombre')
                    address_business = r.get('direccion')
                    district = r.get('distrito')
                    province = r.get('provincia')
                    dep_city = r.get('departamento')
                    result = business_name
                    address = address_business + ' - ' + district + ' - ' + province + ' - ' + dep_city
                    return JsonResponse({'result': result, 'address': address}, status=HTTPStatus.OK)
                else:
                    data = {'error': 'NO EXISTE RUC. REGISTRE MANUAL O CORREGIRLO'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


@csrf_exempt
def save_provider(request):
    if request.method == 'POST':
        _ruc = request.POST.get('ruc_provider', '')
        _names_business = request.POST.get('name_provider', '')
        _names = request.POST.get('description_provider', '')
        _telephone = request.POST.get('phone_provider', '')
        _email = request.POST.get('email_provider', '')
        _address = request.POST.get('address_provider', '')
        if _names == '' or _names == None:
            _names = _names_business
        supplier_obj = Supplier(
            ruc=_ruc,
            business_name=_names_business,
            name=_names,
            phone=_telephone,
            email=_email,
            address=_address,
        )
        supplier_obj.save()
        return JsonResponse({
            'message': True,
            'resp': 'Se registro exitosamente',
        }, status=HTTPStatus.OK)


def report_purchases_by_subsidiary(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        return render(request, 'buys/report_purchases_by_subsidiary.html', {
            'formatdate': formatdate,
        })

    elif request.method == 'POST':
        date_initial = str(request.POST.get('id_date_initial'))
        date_final = str(request.POST.get('id_date_final'))
        subsidiary_set = Subsidiary.objects.all()
        purchase_dict = []
        for s in subsidiary_set:
            quantity_total = 0
            subsidiary_item = {
                'id': s.id,
                'name': s.name,
                'purchases': [],
                'quantity_total': 0,
            }
            purchase_set = Purchase.objects.filter(
                subsidiary=s.id,
                purchase_date__range=(date_initial, date_final)).prefetch_related(
                Prefetch(
                    'purchasedetail_set', queryset=PurchaseDetail.objects.select_related('unit', 'product')
                )
            ).select_related('supplier')

            for p in purchase_set:
                client_reference = ''
                address = ''
                if p.client_reference is not None:
                    client_reference = p.client_reference.names
                if p.delivery_address is not None:
                    address = p.delivery_address

                item_purchase = {
                    'id': p.id,
                    'oc_number': p.bill_number,
                    'client_reference': client_reference.upper(),
                    'address': address.upper(),
                    'date': p.purchase_date,
                    'observations': p.observation,
                    'purchase_detail': [],
                    'rowspan': p.purchasedetail_set.count(),
                }
                for pd in p.purchasedetail_set.all():
                    item_purchase_detail = {
                        'id': pd.id,
                        'quantity': round(pd.quantity, 0),
                        'product': pd.product.name,
                    }
                    quantity_total += round(pd.quantity, 0)
                    item_purchase.get('purchase_detail').append(item_purchase_detail)
                subsidiary_item.get('purchases').append(item_purchase)
            subsidiary_item['quantity_total'] = quantity_total
            purchase_dict.append(subsidiary_item)
        # print(purchase_dict)
        tpl = loader.get_template('buys/report_purchases_by_subsidiary_grid.html')
        context = ({
            'purchase_dict': purchase_dict,
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def supplier_list(request):
    if request.method == 'GET':
        supplier_set = Supplier.objects.all().order_by('id')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        return render(request, 'buys/supplier_list.html', {
            'formatdate': formatdate,
            'supplier_set': supplier_set,
            'districts': District.objects.all().order_by('description'),
        })


def modal_supplier_create(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")

        t = loader.get_template('buys/supplier_create.html')
        c = ({
            'date_now': date_now,
            'districts': District.objects.all(),
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def save_supplier(request):
    if request.method == 'GET':
        supplier_request = request.GET.get('supplier', '')
        data_supplier = json.loads(supplier_request)

        document_number = str(data_supplier["document_number"])
        names = str(data_supplier["names"])
        phone = str(data_supplier["phone"])
        email = str(data_supplier["email"])
        contact_name = str(data_supplier["contact_name"])

        supplier_obj = Supplier(
            name=names.upper(),
            business_name=names.upper(),
            ruc=document_number,
            phone=phone,
            email=email,
            contact_names=contact_name.upper(),
        )
        supplier_obj.save()

        for d in data_supplier['Addresses']:
            new_address = str(d['new_address'])
            district = str(d['district'])
            type_address = str(d['type_address'])

            district_obj = District.objects.get(id=district)

            supplier_address_obj = SupplierAddress(
                supplier=supplier_obj,
                address=new_address.upper(),
                district=district_obj,
                type_address=type_address
            )
            supplier_address_obj.save()

        if data_supplier['accountNumbers'] != '':
            for a in data_supplier['accountNumbers']:
                account_number = str(a['account'])
                bank = str(a['bank'])
                supplier_account_obj = SupplierAccounts(
                    account=account_number,
                    bank=bank,
                    supplier=supplier_obj,
                )
                supplier_account_obj.save()

        return JsonResponse({
            'success': True,
            'message': 'Proveedor Registrado',
        }, status=HTTPStatus.OK)
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def modal_supplier_update(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        supplier_obj = None
        if pk:
            supplier_obj = Supplier.objects.get(id=int(pk))
        t = loader.get_template('buys/supplier_update.html')
        c = ({
            'supplier_obj': supplier_obj,
            'districts': District.objects.all(),
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def update_supplier(request):
    if request.method == 'GET':
        supplier_request = request.GET.get('supplier', '')
        data_supplier = json.loads(supplier_request)
        supplier_id = str(data_supplier["supplier_id"])
        document_number = str(data_supplier["document_number"])
        names = str(data_supplier["names"])
        phone = str(data_supplier["phone"])
        email = str(data_supplier["email"])
        contact_name = str(data_supplier["contact_name"])

        if supplier_id:
            supplier_obj = Supplier.objects.get(id=int(supplier_id))
            supplier_obj.ruc = document_number
            supplier_obj.names = names.upper()
            supplier_obj.business_name = names.upper()
            supplier_obj.phone = phone
            supplier_obj.email = email
            supplier_obj.contact_names = contact_name
            supplier_obj.save()

            supplier_to_delete = SupplierAddress.objects.filter(supplier=supplier_obj)
            supplier_to_delete.delete()

            for d in data_supplier['Addresses']:
                new_address = str(d['new_address'])
                district = str(d['district'])
                type_address = str(d['type_address'])

                district_obj = District.objects.get(id=district)

                supplier_address_obj = SupplierAddress(
                    supplier=supplier_obj,
                    address=new_address.upper(),
                    district=district_obj,
                    type_address=type_address
                )
                supplier_address_obj.save()

            if data_supplier['accountNumbers'] != '':
                supplier_account_to_delete = SupplierAccounts.objects.filter(supplier=supplier_obj)
                supplier_account_to_delete.delete()

                for a in data_supplier['accountNumbers']:
                    account_number = str(a['account'])
                    bank = str(a['bank'])
                    supplier_account_obj = SupplierAccounts(
                        account=account_number,
                        bank=bank.upper(),
                        supplier=supplier_obj,
                    )
                    supplier_account_obj.save()

            return JsonResponse({
                'success': True,
                'message': 'Proveedor Actualizado correctamente',
            }, status=HTTPStatus.OK)
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def contract_list(request):
    if request.method == 'GET':
        contract_set = Contract.objects.all().order_by('id')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        contract_dict = []
        for c in contract_set:
            item_contract = {
                'id': c.id,
                'contract_number': c.contract_number,
                'client': c.client.names,
                'register_date': c.register_date,
                'status': c.get_status_display(),
                'observation': c.observation,
                'contract_detail': []
            }
            for d in c.contractdetail_set.all().order_by('id'):
                purchase = None
                bill_number = None
                guide = None
                guide_serial = None
                guide_correlative = None
                order = None
                order_serial = None
                order_correlative = None
                if d.contractdetailpurchase_set.last():
                    purchase = d.contractdetailpurchase_set.last().purchase.id
                    bill_number = d.contractdetailpurchase_set.last().purchase.bill_number
                if d.guide_set.all():
                    guide = d.guide_set.all().last().id
                    guide_serial = d.guide_set.all().last().serial
                    guide_correlative = d.guide_set.all().last().correlative
                if d.order:
                    order = d.order.id
                    order_serial = d.order.serial
                    order_correlative = d.order.correlative
                item_detail = {
                    'id': d.id,
                    'nro_quota': d.nro_quota,
                    'date': d.date,
                    'purchase': purchase,
                    'bill_number': bill_number,
                    'guide': guide,
                    'guide_serial': guide_serial,
                    'guide_correlative': guide_correlative,
                    'order': order,
                    'order_serial': order_serial,
                    'order_correlative': order_correlative,
                    'contract_detail_item': []
                }
                for e in d.contractdetailitem_set.all():
                    item = {
                        'id': e.id,
                        'product_id': e.product.id,
                        'quantity': e.quantity,
                        'product_name': e.product.name
                    }
                    item_detail.get('contract_detail_item').append(item)
                item_contract.get('contract_detail').append(item_detail)

            contract_dict.append(item_contract)
        # print(contract_dict)

        return render(request, 'buys/contract_list.html', {
            'date_now': formatdate,
            'contract_set': contract_set.order_by('id'),
            'contract_dict': contract_dict,
            'product_set': Product.objects.filter(is_enabled=True)
        })


def modal_contract_create(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")

        t = loader.get_template('buys/contract_create.html')
        c = ({
            'date_now': date_now,
            'client_set': Client.objects.all(),
            'product_set': Product.objects.filter(is_enabled=True),
            'user_set': User.objects.filter(is_active=True, is_superuser=False)
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def save_contract(request):
    if request.method == 'GET':
        contract_request = request.GET.get('contract', '')
        data_contract = json.loads(contract_request)

        client = data_contract["client"]
        number_contract = str(data_contract["number_contract"])
        client_obj = Client.objects.get(id=int(client))

        contract_set = Contract.objects.filter(client=client_obj, contract_number=number_contract)
        if contract_set.exists():
            return JsonResponse({
                'success': False,
                'message': 'EL CONTRATO, YA SE ENCUENTRA REGISTRADO'
            }, status=HTTPStatus.OK)

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        observation = str(data_contract["observation"])
        register_date = str(data_contract["register_date"])
        user_log = data_contract["user"]

        user_log_obj = User.objects.get(id=int(user_log))

        contract_obj = Contract(
            contract_number=number_contract.upper(),
            register_date=register_date,
            client=client_obj,
            observation=observation,
            user=user_log_obj,
            subsidiary=subsidiary_obj,
        )
        contract_obj.save()

        for c in data_contract['dates']:
            date_quota = str(c['date_quota'])
            nro_quota = c['nro_quota']
            contract_detail_obj = ContractDetail(
                contract=contract_obj,
                nro_quota=nro_quota,
                date=date_quota,
            )
            contract_detail_obj.save()
            for i in c['items']:
                product = i['product']
                quantity = i['quantity']
                price_unit = decimal.Decimal(i['price_unit'])
                product_obj = Product.objects.get(id=int(product))
                contract_detail_item_obj = ContractDetailItem(
                    quantity=quantity,
                    product=product_obj,
                    contract_detail=contract_detail_obj,
                    price_unit=price_unit
                )
                contract_detail_item_obj.save()
        return JsonResponse({
            'success': True,
            'message': 'Contrato Registrado',
        }, status=HTTPStatus.OK)
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def modal_update_contract(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")
        pk = int(request.GET.get('pk', ''))
        contract_obj = Contract.objects.get(id=pk)
        sum_quantity = contract_obj.sum_quantity_contract_detail()
        sum_amount = contract_obj.sum_amount_contract_detail()
        # contract_detail_dict = []
        # for cd in contract_obj.contractdetail_set:
        #     item_contract_detail = {
        #         'id': cd.id,
        #         'nro_quota': cd.nro_quota,
        #         'date': cd.date
        #     }
        #     for ci in cd.contractdetailitem_set:
        #         item_c_item = {
        #             'id': ci.id,
        #             'quantity': ci.quantity
        #         }

        t = loader.get_template('buys/contract_update.html')
        c = ({
            'date_now': date_now,
            'client_set': Client.objects.all(),
            'product_set': Product.objects.filter(is_enabled=True),
            'user_set': User.objects.filter(is_active=True, is_superuser=False),
            'contract_obj': contract_obj,
            'sum_quantity': sum_quantity,
            'sum_amount': sum_amount
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def check_oc_update(request):
    if request.method == 'GET':
        contract = int(request.GET.get('contract', ''))
        flag = False
        contract_detail_set = ContractDetail.objects.filter(contract__id=contract)
        for c in contract_detail_set:
            contract_detail_purchase_set = ContractDetailPurchase.objects.filter(contract_detail=c)
            if contract_detail_purchase_set.exists():
                flag = True
                break
        return JsonResponse({
            'status': 'OK',
            'flag': flag,
        }, status=HTTPStatus.OK)


@csrf_exempt
def save_update_contract(request):
    if request.method == 'POST':
        _contract = request.POST.get('contract', '')
        _number_contract = request.POST.get('number_contract_update', '')
        _register_date = request.POST.get('register_date_update', '')
        _client = request.POST.get('client', '')
        _observation = request.POST.get('observations_update', '')
        # _nro_date = request.POST.get('nro-dates', '')
        _user = request.POST.get('user_update', '')
        detail_update = json.loads(request.POST.get('detail_update', ''))

        user_obj = User.objects.get(id=int(_user))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        contract_update_obj = Contract.objects.get(id=int(_contract))
        client_obj = Client.objects.get(id=int(_client))

        contract_update_obj.contract_number = _number_contract
        contract_update_obj.client = client_obj
        contract_update_obj.register_date = _register_date
        contract_update_obj.subsidiary = subsidiary_obj
        contract_update_obj.observation = _observation
        contract_update_obj.user = user_obj
        contract_update_obj.save()

        with transaction.atomic():
            contract_detail_to_delete = ContractDetail.objects.filter(contract=contract_update_obj)
            if contract_detail_to_delete.exists():
                contract_detail_item_to_delete = ContractDetailItem.objects.filter(
                    contract_detail__in=contract_detail_to_delete)
                contract_detail_item_to_delete.delete()
                contract_detail_to_delete.delete()

        for d in detail_update:
            # contract_detail = int(d['contract_detail'])
            nro_quota = str(d['nro_quota'])
            date_quota = str(d['date_quota'])
            new_contract_detail_obj = ContractDetail(
                contract=contract_update_obj,
                nro_quota=nro_quota,
                date=date_quota,
            )
            new_contract_detail_obj.save()
            for i in d['items']:
                product = i['product']
                quantity = i['quantity']
                price_unit = decimal.Decimal(i['price_unit'])
                product_obj = Product.objects.get(id=int(product))
                new_contract_detail_item_obj = ContractDetailItem(
                    quantity=quantity,
                    product=product_obj,
                    contract_detail=new_contract_detail_obj,
                    price_unit=price_unit
                )
                new_contract_detail_item_obj.save()
        return JsonResponse({
            'success': True,
            'message': 'CONTRATO ACTUALIZADO'
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error contactar con sistemas'}, status=HTTPStatus.BAD_REQUEST)


def assign_store_modal(request):
    if request.method == 'GET':
        array_purchases = request.GET.get('array_purchases', '')
        print(array_purchases)

        t = loader.get_template('buys/assign_store_modal.html')
        c = ({
            'client_set': Client.objects.all(),
            'product_set': Product.objects.filter(is_enabled=True)
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def bill_list(request):
    if request.method == 'GET':
        purchase_set = Purchase.objects.all().order_by('id')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        users = User.objects.all()

        return render(request, 'buys/bill_list.html', {
            'formatdate': formatdate,
            'purchase_set': purchase_set,
            'users': users,
        })


def get_purchase_detail(request):
    if request.method == 'GET':
        purchase_id = request.GET.get('id', '')
        detail_purchase_dict = []
        detail_purchase_set = PurchaseDetail.objects.filter(purchase_id=purchase_id)
        for d in detail_purchase_set:
            detail_total = d.price_unit * d.quantity
            item = {
                'id': d.id,
                'purchase_id': d.purchase.id,
                'quantity': round(d.quantity, 2),
                'price_unit': round(d.price_unit, 2),
                'detail_total': round(d.multiplicate(), 2),
                'unit_id': d.unit.id,
                'unit_name': d.unit.name,
                'product_id': d.product.id,
                'product_name': d.product.name,
                'product_code': d.product.code
            }
            detail_purchase_dict.append(item)

        return JsonResponse({
            'message': 'Agregado.',
            'detail_purchase_dict': detail_purchase_dict
        }, status=HTTPStatus.OK)


def update_purchase(request, pk=None):
    contract_obj = None
    purchase_detail_dict = []
    purchase_obj = Purchase.objects.get(id=int(pk))
    client_reference_address_set = ''
    client_reference_entity_address_set = ''

    supplier_address_set = SupplierAddress.objects.filter(supplier=purchase_obj.supplier)
    if purchase_obj.client_reference:
        client_reference_address_set = ClientAddress.objects.filter(client__id=purchase_obj.client_reference.id)
    if purchase_obj.client_reference_entity:
        client_reference_entity_address_set = ClientAddress.objects.filter(
            client__id=purchase_obj.client_reference_entity.id)

    contract_detail_purchase_set = ContractDetailPurchase.objects.filter(purchase=purchase_obj)

    contract_detail_ids_str = ''
    if contract_detail_purchase_set.exists():
        contract_detail_purchase_set_obj = contract_detail_purchase_set.last()
        contract_obj = contract_detail_purchase_set_obj.contract_detail.contract
        contract_detail_ids = [str(obj.contract_detail.id) for obj in contract_detail_purchase_set]
        contract_detail_ids_str = ','.join(contract_detail_ids)

    for pd in purchase_obj.purchasedetail_set.all():
        product_detail = ProductDetail.objects.get(product=pd.product, unit__id=pd.unit.id)
        quantity_x_und = (pd.quantity * product_detail.quantity_minimum).quantize(decimal.Decimal('0.00'),
                                                                                  rounding=decimal.ROUND_UP)
        total_detail = (pd.price_unit * pd.quantity).quantize(decimal.Decimal('0.0000'),
                                                              rounding=decimal.ROUND_HALF_EVEN)
        item = {
            'id': pd.id,
            'product_id': pd.product.id,
            'product_name': pd.product.name,
            'product_brand': pd.product.product_brand.name,
            'quantity': round(pd.quantity, 2),
            'unit_id': pd.unit.id,
            'unit_name': pd.unit.name,
            'quantity_minimum': round(product_detail.quantity_minimum, 0),
            'quantity_x_und': quantity_x_und,
            'units': [],
            'price_unit': pd.price_unit.quantize(decimal.Decimal('0.000000'), rounding=decimal.ROUND_HALF_EVEN),
            'total_detail': total_detail
        }
        for u in ProductDetail.objects.filter(product_id=pd.product.id):
            item_units = {
                'id': u.unit.id,
                'name': u.unit.name,
                'quantity_minimum': round(u.quantity_minimum, 0),
            }
            item.get('units').append(item_units)
        purchase_detail_dict.append(item)
    # print(purchase_detail_dict)
    return render(request, 'buys/buy_list_edit.html', {
        'purchase': purchase_obj,
        'contract_obj': contract_obj,
        'contract_detail_purchase_set': contract_detail_purchase_set,
        'contract_detail_ids_str': contract_detail_ids_str,
        'supplier_set': Supplier.objects.all(),
        'choices_payments_purchase': Purchase._meta.get_field('payment_method').choices,
        'client_set': Client.objects.all(),
        'subsidiary_set': Subsidiary.objects.all().order_by('id'),
        'supplier_address_set': supplier_address_set,
        'client_reference_address_set': client_reference_address_set,
        'client_reference_entity_address_set': client_reference_entity_address_set,
        # 'contract_dict': contract_dict,
        'purchase_detail_dict': purchase_detail_dict,
    })


def get_purchases_by_client(request):
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        purchase_set = Purchase.objects.filter(client_reference__id=client_id).order_by('id')
        return JsonResponse({
            'purchase_set': serializers.serialize('json', purchase_set),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def save_update_purchase(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        purchase_obj = None
        purchase_request = request.GET.get('purchase', '')
        data_purchase = json.loads(purchase_request)
        supplier_id = str(data_purchase["SupplierId"])
        date = str(data_purchase["Date"])
        reference = str(data_purchase["Reference"])
        date_delivery = str(data_purchase["Date"])
        if str(data_purchase["Delivery_date"]):
            date_delivery = str(data_purchase["Delivery_date"])
        type_pay = str(data_purchase["Type_Pay"])
        pay_condition = str(data_purchase["Pay_condition"])
        base_total = decimal.Decimal(data_purchase["Base_Total"])
        igv_total = decimal.Decimal(data_purchase["Igv_Total"])
        total = decimal.Decimal(data_purchase["Import_Total"])
        check_igv = str(data_purchase["Check_Igv"])
        check_dollar = str(data_purchase["Check_Dollar"])
        client_reference = int(data_purchase["client_reference_id"])
        client_entity = data_purchase["client_final"]

        check_subsidiary = str(data_purchase["check-subsidiary"])
        check_provider = str(data_purchase["check-provider"])
        check_client_entity = str(data_purchase["check-client-final"])
        check_client_reference = str(data_purchase["check-client"])

        address_subsidiary = data_purchase["address_subsidiary"]
        address_provider = data_purchase["address_provider"]
        client_address_reference = data_purchase["client_address_reference"]
        client_address_entity = data_purchase["client_final_address"]

        observations = str(data_purchase["observations"])
        contract_detail_obj = None
        contract_detail_id = ''
        date = date_now
        if contract_detail_id:
            date = str(data_purchase["Date"])
            contract_detail_obj = ContractDetail.objects.get(id=int(contract_detail_id))
            contract_detail_id = contract_detail_obj.id
        supplier_obj = Supplier.objects.get(id=int(supplier_id))

        currency_type = 'S'
        if check_dollar == '1':
            currency_type = 'D'
        client_reference_obj = None
        delivery_choice = ''
        city = ''

        if client_reference:
            client_reference_obj = Client.objects.get(id=int(client_reference))
        client_entity_obj = None
        if client_entity:
            client_entity_obj = Client.objects.get(id=int(client_entity))
        delivery_address = ''
        subsidiary_address_obj = None
        address_provider_obj = None
        client_address_obj = None

        if check_subsidiary == '1':
            subsidiary_address_obj = Subsidiary.objects.get(id=int(address_subsidiary))
            delivery_address = subsidiary_address_obj.address
            delivery_choice = 'S'
            city = subsidiary_address_obj.district.description
        elif check_provider == '1':
            address_provider_set = SupplierAddress.objects.filter(id=int(address_provider))
            delivery_choice = 'P'
            if address_provider_set.exists():
                address_provider_obj = address_provider_set.last()
                delivery_address = address_provider_obj.address
                city = address_provider_obj.district.description

        elif check_client_reference == '1':
            client_address_referencer_set = ClientAddress.objects.filter(id=int(client_address_reference))
            delivery_choice = 'CR'
            if client_address_referencer_set.exists():
                client_address_obj = client_address_referencer_set.last()
                delivery_address = client_address_obj.address
                city = client_address_obj.district.description

        elif check_client_entity == '1':
            client_address_entity_set = ClientAddress.objects.filter(id=int(client_address_entity))
            delivery_choice = 'CP'
            if client_address_entity_set.exists():
                client_address_obj = client_address_entity_set.last()
                delivery_address = client_address_obj.address
                city = client_address_obj.district.description

        correlative = int(data_purchase["correlative"])
        _bill_number = f'OC-{datetime.now().year}-{str(correlative).zfill(4)}'
        try:
            purchase_id = request.GET.get('purchase_id', '')
            purchase_obj = Purchase.objects.get(id=purchase_id)
        except Purchase.DoesNotExist:
            purchase_id = 0

        if purchase_id == 0:
            data = {'error': 'NO EXISTE COMPRA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        else:
            purchase_obj.supplier = supplier_obj
            purchase_obj.purchase_date = date
            purchase_obj.user = user_obj
            purchase_obj.subsidiary = subsidiary_obj
            purchase_obj.bill_number = _bill_number
            purchase_obj.payment_method = type_pay
            purchase_obj.payment_condition = pay_condition
            purchase_obj.currency_type = currency_type
            purchase_obj.client_reference = client_reference_obj
            purchase_obj.client_reference_entity = client_entity_obj
            purchase_obj.delivery_address = delivery_address.upper()
            purchase_obj.delivery_choice = delivery_choice
            purchase_obj.observation = observations.upper()
            purchase_obj.city = city.upper()
            purchase_obj.contract_detail = contract_detail_obj
            purchase_obj.delivery_date = date_delivery
            purchase_obj.correlative = correlative
            purchase_obj.reference = reference
            purchase_obj.delivery_subsidiary = subsidiary_address_obj
            purchase_obj.delivery_supplier = address_provider_obj
            purchase_obj.delivery_client = client_address_obj
            purchase_obj.save()

            for detail in data_purchase['Details']:
                product_id = int(detail['Product'])
                product_obj = Product.objects.get(id=product_id)
                unit_id = int(detail['Unit'])
                unit_obj = Unit.objects.get(id=unit_id)
                quantity = str(detail['Quantity'])
                quantity_units = decimal.Decimal(detail['QuantityUnits'])
                price = decimal.Decimal(detail['Price'])

                if detail['ProductDetail'] != 'NaN':
                    product_detail_id = int(detail['ProductDetail'])
                    purchase_detail_obj = PurchaseDetail.objects.get(id=product_detail_id)

                    purchase_detail_obj.purchase = purchase_obj
                    purchase_detail_obj.product = product_obj
                    purchase_detail_obj.quantity = quantity_units
                    purchase_detail_obj.unit = unit_obj
                    purchase_detail_obj.price_unit = price
                    purchase_detail_obj.save()

                else:
                    new_purchase_detail_obj = PurchaseDetail(
                        purchase=purchase_obj,
                        product=product_obj,
                        quantity=quantity_units,
                        unit=unit_obj,
                        price_unit=price
                    )
                    new_purchase_detail_obj.save()

        return JsonResponse({
            'pk': purchase_obj.id,
            'message': 'COMPRA ACTUALIZADA CORRECTAMENTE.',
            'contract': contract_detail_id
        }, status=HTTPStatus.OK)


def get_client(request):
    if request.method == 'GET':
        search = request.GET.get('search')
        client = []
        if search:
            client_set = Client.objects.filter(names__icontains=search)
            for c in client_set:
                client_address_set = c.clientaddress_set.all()
                if client_address_set.exists():
                    address_dict = [{
                        'id': cd.id,
                        'address': cd.address,
                        'district': cd.district.description if cd.district else '-',
                        'reference': cd.reference
                    } for cd in client_address_set]
                else:
                    address_dict = []

                client.append({
                    'id': c.id,
                    'names': c.names,
                    'type_client_display': c.get_type_client_display(),
                    'type_client': c.type_client,
                    'number_document': c.clienttype_set.last().document_number,
                    'address': address_dict,
                    'last_address': c.clientaddress_set.last().address if c.clientaddress_set.last() else '-'
                })

        return JsonResponse({
            'status': True,
            'client': client
        })


def modal_new_guide(request):
    if request.method == 'GET':
        contract_id = request.GET.get('contract_id')
        if contract_id:
            user_id = request.user.id
            user_obj = User.objects.get(id=int(user_id))
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            contract_obj = Contract.objects.get(id=int(contract_id))
            my_date = datetime.now()
            formatdate = my_date.strftime("%Y-%m-%d")
            truck_set = Truck.objects.all()
            # pilot_set = Driver.objects.all()
            motive_set = GuideMotive.objects.filter(type='S')
            district_set = District.objects.all()
            subsidiary_set = Subsidiary.objects.all()
            t = loader.get_template('buys/model_new_guide.html')
            c = ({
                'truck_set': truck_set,
                # 'pilot_set': pilot_set,
                'date': formatdate,
                'motive_set': motive_set,
                'district_set': district_set,
                'subsidiary_obj': subsidiary_obj,
                'subsidiary_set': subsidiary_set,
                'contract_obj': contract_obj
            })
            return JsonResponse({
                'success': True,
                'form': t.render(c, request),
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No se puedo obtener el Contrato, Actualice'
            }, status=HTTPStatus.OK)


def delete_item_buys(request):
    if request.method == 'GET':
        detail_id = request.GET.get('detail_id')
        if detail_id:
            detail_obj = PurchaseDetail.objects.get(id=int(detail_id))
            detail_obj.delete()
            return JsonResponse({
                'success': True,
                'message': 'Detalle eliminado correctamente'
            }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'success': False,
                'message': 'No se puedo obtener el Detalle, Actualice la pag'
            }, status=HTTPStatus.OK)


def get_purchase_form(request):
    if request.method == 'GET':
        supplier_set = Supplier.objects.all().order_by('id')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        return render(request, 'buys/purchase_form.html', {
            'formatdate': formatdate,
            'supplier_set': supplier_set,
            'type_options': Purchase._meta.get_field('payment_method').choices,
            'stores': SubsidiaryStore.objects.all()
        })


def get_product(request):
    if request.method == 'GET':
        search = request.GET.get('search')
        product_list = []
        if search:
            product_set = Product.objects.filter(name__icontains=search, is_enabled=True).select_related(
                'product_family', 'product_brand').order_by('id')
            for c in product_set:
                item_product_list = {
                    'id': c.id,
                    'name': c.name,
                    'brand': c.product_brand.name,
                    'unit_dict': [],
                }
                if c.productdetail_set.exists():
                    for pd in c.productdetail_set.all():
                        item_unit = {
                            'unit_id': pd.unit.id,
                            'unit_name': pd.unit.name,
                            'price_sale': pd.price_sale,
                            'price_purchase': pd.price_purchase,
                            'quantity_minimum': pd.quantity_minimum
                        }
                        item_product_list.get('unit_dict').append(item_unit)
                product_list.append(item_product_list)

        return JsonResponse({
            'status': True,
            'product': product_list
        })


@csrf_exempt
def create_purchase(request):
    if request.method == 'POST':
        _document = request.POST.get('document-type', '')
        _document_number = request.POST.get('document-number', '')
        _supplier = request.POST.get('supplier', '')
        _store_id = request.POST.get('store-id', '')
        _way_to_pay = request.POST.get('way-to-pay', '')
        _money_type = request.POST.get('money-type', '')
        _purchase_date = request.POST.get('purchase-date', '')
        _issue_date = request.POST.get('issue-date', '')
        _observation = request.POST.get('observation', '')
        _base_total = request.POST.get('base-total', '')
        _igv_total = request.POST.get('igv-total', '')
        _total = request.POST.get('total', '')

        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        detail = json.loads(request.POST.get('detail', ''))

        supplier_obj = Supplier.objects.get(id=int(_supplier))
        store_obj = None
        if _store_id and _store_id != '0':
            store_obj = SubsidiaryStore.objects.get(id=int(_store_id))

        order_buy_obj = OrderBuy(
            order_number=_document_number.upper(),
            supplier=supplier_obj,
            payment_method=_way_to_pay,
            currency_type=_money_type,
            order_date=_purchase_date,
            issue_date=_issue_date,
            observation=_observation,
            store_destiny=store_obj,
            subsidiary=subsidiary_obj,
            user=user_obj
        )
        order_buy_obj.save()

        for d in detail:
            product_id = int(d['product'])
            product_obj = Product.objects.get(id=product_id)
            unit_id = int(d['unit'])
            unit_obj = Unit.objects.get(id=unit_id)
            quantity = str(d['quantity'])
            price = decimal.Decimal(d['price'])

            order_detail_buy_obj = OrderBuyDetail(
                quantity=quantity,
                product=product_obj,
                unit=unit_obj,
                price_unit=price,
                order_buy=order_buy_obj
            )
            order_detail_buy_obj.save()

        return JsonResponse({
            'success': True,
            'message': 'Compra registrada con exito'
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error contactar con sistemas'}, status=HTTPStatus.BAD_REQUEST)


def report_contracts(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%d-%m-%Y")
        contract_detail_set = ContractDetail.objects.all().select_related('contract', 'contract__client')
        contract_detail_dict = []
        for c in contract_detail_set:
            c_datetime = datetime.combine(c.date, datetime.min.time())
            difference_date = (c_datetime - my_date).days
            item = {
                'id': c.id,
                'contract_number': c.contract.contract_number,
                'client': c.contract.client.names,
                'nro_quota': c.nro_quota,
                'date': c.date,
                'difference_date': difference_date,
            }
            contract_detail_dict.append(item)

        return render(request, 'buys/report_contracts_detail.html', {
            'formatdate': formatdate,
            'contract_detail_dict': contract_detail_dict,
            'contracts': Contract.objects.all().prefetch_related(
                Prefetch('contractdetail_set', queryset=ContractDetail.objects.select_related('order').prefetch_related(
                    Prefetch('contractdetailitem_set', queryset=ContractDetailItem.objects.select_related('product')),
                    Prefetch('contractdetailpurchase_set', queryset=ContractDetailPurchase.objects.select_related('purchase'))
                ).order_by('id'))
            ).order_by('id'),
        })


def get_details_by_buy(request):
    if request.method == 'GET':
        parent_id = request.GET.get('parent_id', '')
        purchase_id = request.GET.get('purchase_id', '')
        purchase_parent_obj = Purchase.objects.get(pk=int(parent_id))
        purchase_set = Purchase.objects.filter(pk=int(purchase_id))
        purchase_obj = ''
        if purchase_set.exists():
            purchase_obj = purchase_set.last()
        details_parent_purchase = PurchaseDetail.objects.filter(purchase=purchase_parent_obj)
        t = loader.get_template('buys/details_buys_store.html')
        c = ({
            'details_parent': details_parent_purchase,
            'purchase_obj': purchase_obj,
        })
        return JsonResponse({
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)


def buys_credit_note(request):
    if request.method == 'GET':
        purchase_detail_id = request.GET.get('purchase_detail_id', '')
        purchase_id = request.GET.get('purchase_id', '')
        purchase_obj = Purchase.objects.get(id=int(purchase_id))
        purchase_detail_obj = PurchaseDetail.objects.get(id=int(purchase_detail_id))
        bill_serial = '-'
        bill_correlative = '-'
        bill_purchase_set = BillPurchase.objects.filter(purchase=purchase_obj)
        if bill_purchase_set.exists():
            bill_purchase_obj = bill_purchase_set.last()
            bill_serial = bill_purchase_obj.bill.serial
            bill_correlative = bill_purchase_obj.bill.correlative

        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")
        t = loader.get_template('buys/modal_credit_note.html')
        c = ({
            'purchase_detail_obj': purchase_detail_obj,
            'bill_serial': bill_serial,
            'bill_correlative': bill_correlative,
            'date': date_now,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def save_credit_note(request):
    if request.method == 'POST':
        nro_document = request.POST.get('nro-document', '')
        date_issue = request.POST.get('date-issue', '')
        bill_serial = request.POST.get('bill-serial', '')
        bill_correlative = request.POST.get('bill-correlative', '')
        detail = json.loads(request.POST.get('detail', ''))
        purchase_obj = None
        purchase_detail_id = ''
        for detail in detail:
            purchase_detail_id = int(detail['purchaseDetail'])
            purchase_detail_obj = PurchaseDetail.objects.get(id=int(purchase_detail_id))
            purchase_obj = purchase_detail_obj.purchase
            # parent_purchase_id = purchase_obj.parent_purchase.id
        bill_obj = Bill.objects.get(serial=bill_serial, correlative=bill_correlative)
        CreditNote.objects.create(nro_document=nro_document, issue_date=date_issue, bill=bill_obj,
                                  purchase=purchase_obj)

        return JsonResponse({
            'message': 'Nota de Credito registrada',
            'parent': purchase_obj.id,
            'purchase_detail_id': purchase_detail_id,
            'nro_document': nro_document,
            'bill': str(bill_obj)
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)
