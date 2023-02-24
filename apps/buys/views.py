from django.shortcuts import render
import decimal
import json
from datetime import datetime
from http import HTTPStatus

from django.contrib.auth.models import User
from django.core import serializers
from django.db.models import Q, Sum, F, Prefetch, Subquery, OuterRef
from django.http import JsonResponse
from django.shortcuts import render
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from apps.hrm.models import Subsidiary
from apps.hrm.views import get_subsidiary_by_user
from apps.sales.views import kardex_input, kardex_ouput, kardex_initial, calculate_minimum_unit, \
    save_loan_payment_in_cash_flow
from .models import *
from ..sales.models import Product, Unit, Supplier, SubsidiaryStore, ProductStore, ProductDetail, Kardex, Cash, \
    CashFlow, TransactionPayment


class Home(TemplateView):
    template_name = 'buys/home.html'


def purchase_form(request):
    # form_obj = FormGuide()
    # programmings = Programming.objects.filter(status__in=['P']).order_by('id')
    supplier_obj = Supplier.objects.all()
    product_obj = Product.objects.all()
    unitmeasurement_obj = Unit.objects.all()
    truck_set = Truck.objects.all()
    return render(request, 'buys/purchase_form.html', {
        # 'form': form_obj,
        'supplier_obj': supplier_obj,
        'unitmeasurement_obj': unitmeasurement_obj,
        'product_obj': product_obj,
        'truck_set': truck_set,
        # 'list_detail_purchase': get_employees(need_rendering=False),
    })


@csrf_exempt
def save_purchase(request):
    if request.method == 'GET':
        purchase_request = request.GET.get('purchase', '')
        # print(purchase_request)
        data_purchase = json.loads(purchase_request)
        # print(data_purchase)

        provider_id = str(data_purchase["ProviderId"])
        type_bill = str(data_purchase["Type_bill"])
        date = str(data_purchase["Date"])
        invoice = str(data_purchase["Invoice"])
        print(data_purchase["truck"])
        if (data_purchase["truck"]) is not None:
            truck_id = int(data_purchase["truck"])
            truck_obj = Truck.objects.get(id=truck_id)
            status = 'A'
        else:
            truck_obj = None
            status = 'S'
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))

        subsidiary_obj = get_subsidiary_by_user(user_obj)
        print(subsidiary_obj)
        supplier_obj = Supplier.objects.get(id=int(provider_id))

        purchase_obj = Purchase(
            supplier=supplier_obj,
            purchase_date=date,
            bill_number=invoice,
            user=user_obj,
            subsidiary=subsidiary_obj,
            truck=truck_obj,
            status=status,
            type_bill=type_bill,
        )
        purchase_obj.save()

        for detail in data_purchase['Details']:
            quantity = decimal.Decimal(detail['Quantity'])
            price = decimal.Decimal(detail['Price'])
            # recuperamos del producto
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)

            # recuperamos la unidad
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)

            new_purchase_detail = {
                'purchase': purchase_obj,
                'product': product_obj,
                'quantity': quantity,
                'unit': unit_obj,
                'price_unit': price,
            }
            new_purchase_detail_obj = PurchaseDetail.objects.create(**new_purchase_detail)
            new_purchase_detail_obj.save()

        return JsonResponse({
            'message': 'COMPRA REGISTRADA CORRECTAMENTE.',

        }, status=HTTPStatus.OK)


# guardar detalle de compras en almacenes
@csrf_exempt
def save_detail_purchase_store(request):
    if request.method == 'GET':
        purchase_request = request.GET.get('details_purchase', '')
        # print(purchase_request)
        data_purchase = json.loads(purchase_request)
        # print(data_purchase)
        purchase_id = str(data_purchase["Purchase"])
        subsidiary_store_id = int(data_purchase["id_almacen"])
        purchase_obj = Purchase.objects.get(id=int(purchase_id))
        # CONSULTA SI LA COMPRA YA ESTA EN ALMACEN Y ROMPE LA SECUENCIA
        if purchase_obj.status == 'A':
            data = {'error': 'LOS PRODUCTOS YA ESTAN ASIGNADOS A SU ALMACEN.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        # user_id = request.user.id
        # user_obj = User.objects.get(id=int(user_id))
        # subsidiary_obj = get_subsidiary_by_user(user_obj)

        try:
            subsidiary_store_obj = SubsidiaryStore.objects.get(id=subsidiary_store_id)
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'NO EXISTE ALMACEN DE MERCADERIA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for detail in data_purchase['Details']:
            print(detail['Quantity'])
            quantity = decimal.Decimal((detail['Quantity']).replace(",", "."))
            price = decimal.Decimal((detail['Price']).replace(",", "."))
            # recuperamos del producto
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)

            # recuperamos la unidad
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)

            # store_id = int(detail['Store'])
            # store_obj = SubsidiaryStore.objects.get(id=store_id)

            try:
                product_store_obj = ProductStore.objects.get(product=product_obj, subsidiary_store=subsidiary_store_obj)
            except ProductStore.DoesNotExist:
                product_store_obj = None
            unit_min_detail_product = ProductDetail.objects.get(product=product_obj, unit=unit_obj).quantity_minimum

            purchase_detail = int(detail['PurchaseDetail'])
            purchase_detail_obj = PurchaseDetail.objects.get(id=purchase_detail)

            if product_store_obj is None:
                new_product_store_obj = ProductStore(
                    product=product_obj,
                    subsidiary_store=subsidiary_store_obj,
                    stock=unit_min_detail_product * quantity
                )
                new_product_store_obj.save()
                kardex_initial(new_product_store_obj, unit_min_detail_product * quantity, price,
                               purchase_detail_obj=purchase_detail_obj)
            else:
                kardex_input(product_store_obj.id, unit_min_detail_product * quantity, price,
                             purchase_detail_obj=purchase_detail_obj)

        purchase_obj.status = 'A'
        purchase_obj.save()
        return JsonResponse({
            'message': 'PRODUCTO(S) ALMACENADO',

        }, status=HTTPStatus.OK)


def requirement_buy_create(request):
    # form_obj = FormGuide()
    # programmings = Programming.objects.filter(status__in=['P']).order_by('id')
    supplier_obj = Supplier.objects.all()
    unitmeasurement_obj = Unit.objects.all()
    product_obj = Product.objects.filter(is_approved_by_osinergmin=True)
    return render(request, 'buys/requirement_buy_create.html', {
        # 'form': form_obj,
        'supplier_obj': supplier_obj,
        'unitmeasurement_obj': unitmeasurement_obj,
        'product_obj': product_obj,

    })


def get_rateroutes_programming(request):
    # form_obj = FormGuide()
    # programmings = Programming.objects.filter(status__in=['P']).order_by('id')
    truck_obj = Truck.objects.filter(condition_owner='A')
    subsidiary_obj = Subsidiary.objects.all()
    return render(request, 'buys/rate_routes_create.html', {
        # 'form': form_obj,
        'truck_obj': truck_obj,
        'subsidiary_obj': subsidiary_obj,
    })


def requirement_buy_save(request):
    if request.method == 'GET':
        requirement_buy_request = request.GET.get('requirement_buy', '')
        data_requirement_buy = json.loads(requirement_buy_request)

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        date_raquirement = str(data_requirement_buy["id_date_raquirement"])
        number_scop = str(data_requirement_buy["id_number_scop"])
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        new_requirement_buy = {
            'creation_date': date_raquirement,
            'number_scop': number_scop,
            'user': user_obj,
            'subsidiary': subsidiary_obj,
        }
        requirement_buy_obj = Requirement_buys.objects.create(**new_requirement_buy)
        requirement_buy_obj.save()

    for detail in data_requirement_buy['Details']:
        quantity = decimal.Decimal(detail['Quantity'])

        # recuperamos del producto
        product_id = int(detail['Product'])
        product_obj = Product.objects.get(id=product_id)

        # recuperamos la unidad
        unit_id = int(detail['Unit'])
        unit_obj = Unit.objects.get(id=unit_id)

        new_detail_requirement_buy = {
            'product': product_obj,
            'requirement_buys': requirement_buy_obj,
            'quantity': quantity,
            'unit': unit_obj,

        }
        new_detail_requirement_buy = RequirementDetail_buys.objects.create(**new_detail_requirement_buy)
        new_detail_requirement_buy.save()

        # recuperamos del almacen
        # store_id = int(detail['Store'])
        #
        # kardex_ouput(store_id, quantity)

    return JsonResponse({
        'message': 'Se guardo la guia correctamente.',
        'requirement_buy': requirement_buy_obj.id,

    }, status=HTTPStatus.OK)


def get_requeriments_buys_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    requiriments_buys = Requirement_buys.objects.filter(subsidiary__id=subsidiary_obj.id, status='1').order_by(
        "creation_date")
    return render(request, 'buys/requirement_buy_list.html', {
        'requiriments_buys': requiriments_buys
    })


def get_purchase_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    purchases = Purchase.objects.filter(subsidiary=subsidiary_obj, status='S')
    return render(request, 'buys/purchase_list.html', {
        'purchases': purchases
    })


def get_purchase_store_list(request):
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
            purchases_store = Purchase.objects.filter(subsidiary=subsidiary_obj, status='A',
                                                      purchase_date__range=(
                                                          date_initial, date_final)).distinct('id')
            # purchases_store_serializers = serializers.serialize('json', purchases_store)
            tpl = loader.get_template('buys/purchase_store_grid_list.html')
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
            return render(request, 'buys/purchase_store_list.html', {
                # 'purchases_store': purchases_store,
                'date_now': date_now,
            })


def get_purchase_annular_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    purchases_annular = Purchase.objects.filter(subsidiary=subsidiary_obj, status='N')
    return render(request, 'buys/purchase_annular_list.html', {
        'purchases_annular': purchases_annular
    })


def get_detail_purchase_store(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        purchase_obj = Purchase.objects.get(id=pk)
        purchase_details = PurchaseDetail.objects.filter(purchase=purchase_obj)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        # subsidiary_stores = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj)
        # if purchase_obj.status == 'A':
        #     data = {'error': 'LOS PRODUCTOS YA ESTAN ASIGNADOS A SU ALMACEN.'}
        #     response = JsonResponse(data)
        #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        #     return response
        try:
            # subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj)
            subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='M')
        except SubsidiaryStore.DoesNotExist:
            data = {'detalle': 'NO EXISTE ALMACEN DE MERCADERIA'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        t = loader.get_template('buys/assignment_detail_purchase.html')
        c = ({
            'purchase': purchase_obj,
            'detail_purchase': purchase_details,
            'subsidiary_stores': subsidiary_store_obj,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def get_requirement_programming(request):
    if request.method == 'GET':
        truck_obj = Truck.objects.all()
        programmings = RequirementBuysProgramming.objects.filter(status='P')
        t = loader.get_template('buys/programming_requirement_buy.html')
        c = ({
            'truck_obj': truck_obj,
            'programmings': programmings,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def get_programming_invoice(request):
    if request.method == 'GET':
        programmign_buy_obj = RequirementBuysProgramming.objects.filter(status='P')
        requirement_buys = Requirement_buys.objects.filter(status=2)
        subsidiary_store_obj = SubsidiaryStore.objects.filter(category='I')
        today = datetime.now()
        fomat_today = today.strftime("%Y-%m-%d")
        t = loader.get_template('buys/programmig_invoice.html')
        c = ({
            # 'requirement_buy_obj': requirement_buy_obj,
            'programmign_buy_obj': programmign_buy_obj,
            'subsidiary_store_obj': subsidiary_store_obj,
            'requirement_buys': requirement_buys,
            'today': fomat_today,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def get_expense_programming(request):
    if request.method == 'GET':
        programmign_buy_obj = RequirementBuysProgramming.objects.filter(status='F')
        t = loader.get_template('buys/programming_expense.html')
        c = ({
            # 'requirement_buy_obj': requirement_buy_obj,
            'choices_type': ProgrammingExpense._meta.get_field('type').choices,
            'programmign_buy_obj': programmign_buy_obj,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


@csrf_exempt
def save_programming_buys(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_programming = my_date.strftime("%Y-%m-%d")

        details_request = request.GET.get('details_send', '')
        data_programming = json.loads(details_request)

        # pk = str(data_programming["pk"])
        # pk_obj = Requirement_buys.objects.get(id=int(pk))
        for detail in data_programming['Details']:
            status = (detail['status'])
            if status == 'R':
                status = 'P'

                number_scop = (detail['Number_scop'])
                truck_id = int(detail['Truck'])
                truck_obj = Truck.objects.get(id=truck_id)

                new_programming_detail = {
                    'date_programming': date_programming,
                    'number_scop': number_scop,
                    'truck': truck_obj,
                    'status': status,

                    # 'requirement_buys': pk_obj,
                }
                new_programming_detail_obj = RequirementBuysProgramming.objects.create(**new_programming_detail)
                new_programming_detail_obj.save()
                return JsonResponse({
                    'message': 'PROGRAMACION REGISTRADA CORRECTAMENTE.',

                }, status=HTTPStatus.OK)

        data = {'error': 'LAS PORGRAMACION YA FUE SE REGISTRARON.'}
        response = JsonResponse(data)
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


def get_units_by_product(request):
    if request.method == 'GET':
        id_product = request.GET.get('ip', '')
        product_obj = Product.objects.get(pk=int(id_product))
        units = Unit.objects.filter(productdetail__product=product_obj)
        units_serialized_obj = serializers.serialize('json', units)

        return JsonResponse({
            'units': units_serialized_obj,
        }, status=HTTPStatus.OK)


def get_units_product(request):
    id_product = request.GET.get('ip', '')
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


def get_products_by_requirement(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='G')
        requirement_id = request.GET.get('ip', '')
        requirement_obj = Requirement_buys.objects.get(pk=int(requirement_id))
        details_requirement = RequirementDetail_buys.objects.filter(requirement_buys=requirement_obj)
        product = Product.objects.filter(requirementdetail_buys__in=details_requirement)
        product_serialized_obj = serializers.serialize('json', product)

        # product_obj = Product.objects.get(pk=int(id_product))
        # units = Unit.objects.filter(productdetail__product=product_obj)
        # units_serialized_obj = serializers.serialize('json', units)

        t = loader.get_template('buys/current_stock.html')
        c = ({
            'details': details_requirement,
            'my_subsidiary_store': subsidiary_store_obj,

        })
        return JsonResponse({
            'scop': requirement_obj.number_scop,
            'creation_date': requirement_obj.creation_date,
            'approval_date': requirement_obj.approval_date,
            'products': product_serialized_obj,
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)


def get_scop_truck(request):
    if request.method == 'GET':
        programming_request = request.GET.get('programming_obj', '')
        data_programming = json.loads(programming_request)
        process = data_programming['process']
        programming = data_programming['programming']
        programing_obj = RequirementBuysProgramming.objects.get(id=programming)
        # deteil_obj = RequirementDetail_buys.objects.get(id=programming)
        truck_obj = Truck.objects.get(truck=programing_obj)
        # requirement = data_programming['requirement']
        # requirement_obj = Requirement_buys.objects.get(id=int(requirement))

        # try:
        #     nscop = RequirementBuysProgramming.objects.get(truck__id=truck_obj.id,
        #                                                    requirement_buys__id=requirement_obj.id)
        #     if (process == 'invoice'):
        #         detail_invoice_obj = Programminginvoice.objects.filter(requirementBuysProgramming=nscop)
        #         # se necesita seriezer cuando envio una lista
        #         detail_serialized_obj = serializers.serialize('json', detail_invoice_obj)
        #     else:
        #         detail_fuel_obj = ProgrammingFuel.objects.filter(requirementBuysProgramming=nscop)
        #         detail_serialized_obj = serializers.serialize('json', detail_fuel_obj)
        # except RequirementBuysProgramming.DoesNotExist:
        #     nscop = None

    return JsonResponse({
        'truck': truck_obj.license_plate,
        'condition_owner': truck_obj.condition_owner,
        # 'deteil_onj': deteil_obj,
        # 'nscop': nscop.number_scop,
        # 'programming': nscop.id,
        # 'detail_serialized': detail_serialized_obj,
        # 'units': serialized_units,
        # 'id_product_store': product_store_obj.id
    }, status=HTTPStatus.OK)


@csrf_exempt
def save_programming_invoice(request):
    if request.method == 'GET':
        details_request = request.GET.get('details_send', '')
        data_invoice = json.loads(details_request)
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        my_subsidiary_obj = get_subsidiary_by_user(user_obj)
        try:
            my_subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=my_subsidiary_obj,
                                                                  category='G')
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'No existe almacen de mercaderia.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for detail in data_invoice['Details']:
            programing = int(detail['programming'])
            programing_obj = RequirementBuysProgramming.objects.get(id=programing)
            requirement = int(detail['requirement'])
            requirement_obj = Requirement_buys.objects.get(id=requirement)
            product = int(detail['product_id'])
            product_obj = Product.objects.get(pk=product)
            unit = int(detail['unit_id'])
            unit_obj = Unit.objects.get(pk=unit)
            # detail_requirement_obj = RequirementDetail_buys.objects.filter(requirement_buys=requirement_obj).first
            # product_obj = Product.objects.get(id=detail_requirement_obj.id)
            guide = (detail['guide'])
            date_arrive = (detail['date_arrive'])
            quantity = decimal.Decimal(detail['quantity'])
            status = (detail['status'])
            other_subsidiary_store = int(detail['store'])
            other_subsidiary_store_obj = SubsidiaryStore.objects.get(pk=other_subsidiary_store)
            if status == 'P':
                new_programming_detail = {
                    'guide': guide,
                    'quantity': quantity,
                    'requirement_buys': requirement_obj,
                    'requirementBuysProgramming': programing_obj,
                    'date_arrive': date_arrive,
                    'status': status,
                    'subsidiary_store_destiny': other_subsidiary_store_obj,
                    'subsidiary_store_origin': my_subsidiary_store_obj,
                }
                new_programming_invoice_obj = Programminginvoice.objects.create(**new_programming_detail)
                new_programming_invoice_obj.save()
                # kardex final
                try:
                    other_product_store_obj = ProductStore.objects.get(product=product_obj,
                                                                       subsidiary_store=other_subsidiary_store_obj)
                except ProductStore.DoesNotExist:
                    other_product_store_obj = None
                my_product_store = ProductStore.objects.get(product=product_obj,
                                                            subsidiary_store=my_subsidiary_store_obj)
                quantity_minimum_unit = calculate_minimum_unit(quantity, unit_obj, product_obj)
                kardex_ouput(my_product_store.id, quantity_minimum_unit,
                             programming_invoice_obj=new_programming_invoice_obj)
                if other_product_store_obj is None:
                    new_product_store_obj = ProductStore(
                        product=product_obj,
                        subsidiary_store=other_subsidiary_store_obj,
                        stock=quantity_minimum_unit
                    )
                    new_product_store_obj.save()

                    kardex_initial(
                        new_product_store_obj,
                        quantity_minimum_unit,
                        my_product_store.kardex_set.last().remaining_price,
                        programming_invoice_obj=new_programming_invoice_obj)
                else:
                    kardex_input(
                        other_product_store_obj.id,
                        quantity_minimum_unit,
                        my_product_store.kardex_set.last().remaining_price,
                        programming_invoice_obj=new_programming_invoice_obj)

                new_programming_invoice_obj.status = 'R'
                new_programming_invoice_obj.save()
        programing_obj.status = 'F'
        programing_obj.save()
        return JsonResponse({
            'message': 'TRASLADO REGISTRADO',

        }, status=HTTPStatus.OK)


# guardar detalle del requerimiento en almacen(kardex)
@csrf_exempt
def save_detail_requirement_store(request):
    if request.method == 'GET':
        id_requirement = request.GET.get('pk', '')
        requirement_obj = Requirement_buys.objects.get(pk=int(id_requirement))
        details_requirements = RequirementDetail_buys.objects.filter(requirement_buys=requirement_obj)
        # CONSULTA SI LA COMPRA YA ESTA EN ALMACEN Y ROMPE LA SECUENCIA
        if requirement_obj.status == '2':
            data = {'error': 'EL REQUERIMIENTO YA ESTA APROBADO.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        try:
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='G')
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'NO EXISTE EL ALMACEN.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for detail in details_requirements:

            quantity = detail.quantity
            price = detail.price
            # recuperamos del producto
            product_obj = detail.product

            # recuperamos la unidad
            unit_obj = detail.unit

            try:
                product_store_obj = ProductStore.objects.get(product=product_obj, subsidiary_store=subsidiary_store_obj)
            except ProductStore.DoesNotExist:
                product_store_obj = None
            unit_min_detail_product = ProductDetail.objects.get(product=product_obj, unit=unit_obj).quantity_minimum

            if product_store_obj is None:
                new_product_store_obj = ProductStore(
                    product=product_obj,
                    subsidiary_store=subsidiary_store_obj,
                    stock=unit_min_detail_product * quantity
                )
                new_product_store_obj.save()
                kardex_initial(new_product_store_obj, unit_min_detail_product * quantity, price,
                               requirement_detail_obj=detail)
            else:
                kardex_input(product_store_obj.id, unit_min_detail_product * quantity, price,
                             requirement_detail_obj=detail)

        requirement_obj.status = '2'
        requirement_obj.save()
        return JsonResponse({
            'message': 'REQUERIMIENTO APROBADO',

        }, status=HTTPStatus.OK)


@csrf_exempt
def save_programming_fuel(request):
    if request.method == 'GET':
        details_request = request.GET.get('details_send', '')
        data_invoice = json.loads(details_request)

        for detail in data_invoice['Details']:
            programming = int(detail['programming'])
            programming_obj = RequirementBuysProgramming.objects.get(id=programming)
            invoice = (detail['invoice'])
            date_invoice = (detail['date_invoice'])
            price = (detail['price'])
            quantity = (detail['quantity'])
            noperation = (detail['noperation'])
            condition_owner = (detail['condition_owner'])
            type = (detail['type'])

            status = (detail['status'])
            if status == 'P':
                status = 'R'
                new_programming_detail = {
                    'invoice': invoice,
                    'date_invoice': date_invoice,
                    'price': price,
                    'quantity': quantity,
                    'noperation': noperation,
                    'requirementBuysProgramming': programming_obj,
                    'status': status,
                    'type': type,
                }
                new_programming_fuel_obj = ProgrammingExpense.objects.create(**new_programming_detail)
                new_programming_fuel_obj.save()

        return JsonResponse({
            'message': 'TANQUEOS REGISTRADOS CORRECTAMENTE.',

        }, status=HTTPStatus.OK)

        # data = {'error': 'LOS TANQUEOS YA SE REGISTRARON.'}
        # response = JsonResponse(data)
        # response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        # return response


@csrf_exempt
def delete_programming_fuel(request):
    if request.method == 'GET':
        details_request = request.GET.get('details_send', '')
        data_invoice = json.loads(details_request)

        pk = int(data_invoice["pk"])
        pk_obj = RequirementBuysProgramming.objects.get(id=pk)

        # new_programming_fuel_obj = ProgrammingFuel.objects.create(**new_programming_detail)
        # new_programming_fuel_obj.save()

        return JsonResponse({
            'message': 'TANQUEOS REGISTRADOS CORRECTAMENTE.',

        }, status=HTTPStatus.OK)

    data = {'error': 'LOS TANQUEOS YA SE REGISTRARON.'}
    response = JsonResponse(data)
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    return response


def get_approve_detail_requirement(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        requirement_buy_obj = Requirement_buys.objects.get(id=pk)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        t = loader.get_template('buys/approve_requirement.html')
        c = ({
            'requirement': requirement_buy_obj,
            'date_now': formatdate,
            'coin_type': RequirementDetail_buys._meta.get_field('coin').choices,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def update_details_requirement_store(request):
    if request.method == 'GET':
        requirement_request = request.GET.get('requirements', '')
        data_requirement = json.loads(requirement_request)
        date_approve = data_requirement['date_approve']
        invoice = data_requirement['invoice']
        id_requirement = data_requirement['pk']
        requirement_obj = Requirement_buys.objects.get(pk=int(id_requirement))
        if requirement_obj.status == '2':
            data = {'error': 'EL REQUERIMIENTO YA ESTA APROBADO.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        try:
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='G')
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'NO EXISTE EL ALMACEN.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        # Actualiza detalle de requerimiento
        for detail in data_requirement['Details']:
            requirement_detail_id = (detail['detail_requirement_id'])
            _price = decimal.Decimal(detail['price'])
            _amount = decimal.Decimal(detail['amount'])
            _coin = int(detail['coin'])
            _change_coin = decimal.Decimal(detail['change_coin'])
            _price_pen = decimal.Decimal(_price * _change_coin)
            _amount_pen = decimal.Decimal(_amount * _change_coin)
            requirement_detail_obj = RequirementDetail_buys.objects.get(id=requirement_detail_id)
            requirement_detail_obj.price = _price
            requirement_detail_obj.amount = _amount
            requirement_detail_obj.price_pen = _price_pen
            requirement_detail_obj.amount_pen = _amount_pen
            requirement_detail_obj.coin = _coin
            requirement_detail_obj.change_coin = _change_coin
            requirement_detail_obj.save()

            try:
                product_store_obj = ProductStore.objects.get(product=requirement_detail_obj.product,
                                                             subsidiary_store=subsidiary_store_obj)
            except ProductStore.DoesNotExist:
                product_store_obj = None
            unit_min_detail_product = ProductDetail.objects.get(product=requirement_detail_obj.product,
                                                                unit=requirement_detail_obj.unit).quantity_minimum

            if product_store_obj is None:
                new_product_store_obj = ProductStore(
                    product=requirement_detail_obj.product,
                    subsidiary_store=subsidiary_store_obj,
                    stock=unit_min_detail_product * requirement_detail_obj.quantity
                )
                new_product_store_obj.save()
                kardex_initial(new_product_store_obj,
                               round(unit_min_detail_product * requirement_detail_obj.quantity, 2),
                               requirement_detail_obj.price, requirement_detail_obj=requirement_detail_obj)
            else:
                kardex_input(product_store_obj.id, round(unit_min_detail_product * requirement_detail_obj.quantity, 2),
                             requirement_detail_obj.price, requirement_detail_obj=requirement_detail_obj)

    requirement_obj.approval_date = date_approve
    requirement_obj.invoice = invoice
    requirement_obj.status = '2'
    requirement_obj.save()
    return JsonResponse({
        'message': 'REQUERIMIENTO APROBADO',

    }, status=HTTPStatus.OK)


def get_list_requirement_stock(request):
    if request.method == 'GET':
        return JsonResponse({
            'message': 'REQUERIMIENTO APROBADO',

        }, status=HTTPStatus.OK)


def get_requirement_balance(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    requirements_obj = Requirement_buys.objects.all().filter(status=2, subsidiary__id=subsidiary_obj.id).order_by('id')
    requirements_total = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
                                                               requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
        Sum('quantity'))
    programming_invoice_total = Programminginvoice.objects.filter(requirement_buys__subsidiary=subsidiary_obj.id,
                                                                  status='R',
                                                                  requirement_buys__status=2).aggregate(
        Sum('quantity'))
    if requirements_total['quantity__sum'] is None:
        requirements_total['quantity__sum'] = 0
        programming_invoice_total['quantity__sum'] = 0
    total_difference = decimal.Decimal(requirements_total['quantity__sum'] - programming_invoice_total['quantity__sum'])
    total_price = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
                                                        requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
        Sum('price'))
    if total_price['price__sum'] is None:
        total_price['price__sum'] = 0
    # total_balance_amount = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
    #                                                              requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
    #     Sum('amount'))
    total_price_pen = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
                                                            requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
        Sum('price_pen'))
    if total_price_pen['price_pen__sum'] is None:
        total_price_pen['price_pen__sum'] = 0
    # total_balance_amount_pen = RequirementDetail_buys.objects.filter(requirement_buys__status=2,
    #                                                                  requirement_buys__subsidiary=subsidiary_obj.id).aggregate(
    #     Sum('price_pen'))

    return render(request, 'buys/requirement_balance.html', {
        'requirements': requirements_obj,
        'requirements_total': requirements_total['quantity__sum'],
        'programming_invoice_total': programming_invoice_total['quantity__sum'],
        'total_difference': total_difference,
        'total_price': total_price['price__sum'],
        # 'total_amount': total_balance_amount['amount__sum'],
        'total_price_pen': total_price_pen['price_pen__sum'],
        # 'total_amount_pen': total_balance_amount_pen['amount_pen__sum'],
    })


def get_programming_by_truck_and_dates(request):
    if request.method == 'GET':
        details_request = request.GET.get('datos', '')
        if details_request != '':
            data_json = json.loads(details_request)
            id_truck = data_json['id_truck']
            date_initial = (data_json['date_initial'])
            date_final = (data_json['date_final'])
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            truck_obj = Truck.objects.get(id=int(id_truck))
            requirementprogramming_obj = RequirementBuysProgramming.objects.filter(
                programminginvoice__requirement_buys__subsidiary=subsidiary_obj, truck=truck_obj, status='F',
                programminginvoice__date_arrive__range=(date_initial, date_final)).distinct('number_scop')

            purchase_detail_set = PurchaseDetail.objects.filter(purchase__subsidiary__id=subsidiary_obj.id,
                                                                purchase__status='A', purchase__truck=truck_obj,
                                                                purchase__purchase_date__range=(date_initial, date_final)).annotate(
                total=Sum(F('price_unit') * F('quantity'))).aggregate(Sum('total'))

            programming_expense_total_price = ProgrammingExpense.objects.filter(
                requirementBuysProgramming__programminginvoice__date_arrive__range=(
                    date_initial, date_final), requirementBuysProgramming__truck=truck_obj,
                requirementBuysProgramming__status='F',
                requirementBuysProgramming__programminginvoice__requirement_buys__subsidiary=subsidiary_obj).aggregate(
                Sum('price'))
            programming_invoice_total_quantity = Programminginvoice.objects.filter(
                date_arrive__range=(date_initial, date_final), requirementBuysProgramming__truck=truck_obj,
                requirementBuysProgramming__status='F',
                requirement_buys__subsidiary=subsidiary_obj, status='R').aggregate(Sum('quantity'))

            tpl = loader.get_template('buys/report_programming_by_truck_and_dates_grid.html')
            context = ({
                # 'programmingsinvoice': programminginvoice_obj,
                'programmings': requirementprogramming_obj,
                'purchases': round(float(purchase_detail_set['total__sum']), 2),
                'total_price': programming_expense_total_price['price__sum'],
                'total_quantity': programming_invoice_total_quantity['quantity__sum'],
            })
            return JsonResponse({
                'success': True,
                'grid': tpl.render(context),
            }, status=HTTPStatus.OK)
        else:
            trucks_obj = Truck.objects.all()
            mydate = datetime.now()
            formatdate = mydate.strftime("%Y-%m-%d")
            return render(request, 'buys/report_programming_by_truck_and_dates.html', {
                'trucks': trucks_obj,
                'date': formatdate
            })


def get_report_context_kardex_glp(subsidiary_obj, pk, is_pdf=False, get_context=False):
    other_subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(pk))  # otro almacen insumos
    my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='G')  # pluspetrol
    my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj,
                                                                 category='I')  # tu almacen insumos

    product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')
    product_store_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)

    kardex_set = Kardex.objects.filter(product_store=product_store_obj)

    tpl = loader.get_template('buys/report_kardex_glp_grid.html')
    context = ({
        'is_pdf': is_pdf,
        'kardex_set': kardex_set,
        'my_subsidiary_store_insume': my_subsidiary_store_insume_obj,
        'other_subsidiary_store': other_subsidiary_store_obj,
    })
    if get_context:
        return context
    else:
        return tpl.render(context)


def validate_report_kardex_glp(my_subsidiary_obj):
    is_valid = True
    error = ''

    try:
        my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(
            subsidiary=my_subsidiary_obj, category='G')  # pluspetrol
    except SubsidiaryStore.DoesNotExist:
        error = 'NO EXISTE ALMACEN PLUSPETROL EN ESTA SEDE.'
        is_valid = False

    try:
        my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(
            subsidiary=my_subsidiary_obj, category='I')  # tu almacen insumos
    except SubsidiaryStore.DoesNotExist:
        error = 'NO EXISTE ALMACEN INSUMOS EN ESTA SEDE.'
        is_valid = False

    try:
        product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')
    except Product.DoesNotExist:
        error = 'NO EXISTE EL PRODUCTO GLP.'
        is_valid = False

    try:
        product_store_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)
    except ProductStore.DoesNotExist:
        error = 'NO EXISTE EL PRODUCTO GLP EN EL ALMACEN DE PLUSPETROL DE ESTA SEDE.'
        is_valid = False

    try:
        my_product_store_supply_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_insume_obj,
                                                               product=product_obj)
    except ProductStore.DoesNotExist:
        error = 'NO EXISTE PRODUCTO GLP EN EL ALMACEN DE INSUMOS DE ESTA SEDE.'
        is_valid = False

    context = ({
        'is_valid': is_valid,
        'error': error,
    })

    return context


def get_report_kardex_glp(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        pk = request.GET.get('option', '')
        date_initial = request.GET.get('date_initial')
        date_final = request.GET.get('date_final')
        if pk != '':
            context = validate_report_kardex_glp(subsidiary_obj)
            if context.get('is_valid'):
                return JsonResponse({
                    'success': True,
                    'grid': get_kardex_dictionary(subsidiary_obj, is_pdf=False, start_date=date_initial,
                                                  end_date=date_final),
                }, status=HTTPStatus.OK)
            else:
                data = {'error': context.get('error')}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
        else:
            mydate = datetime.now()
            formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            return render(request, 'buys/report_kardex_glp.html', {
                'date': formatdate,
                'date_now': date_now,
                'date_initial': date_initial,
                'date_final': date_final,
            })


def sum_inputs_from_subsidiary_store_supplies(
        k_id,
        product_store_obj,
        subsidiary_store_origin_obj,
        subsidiary_store_destiny_obj
):
    k_initial_quantity = 0
    k_inputs_quantity = 0
    query_set = Kardex.objects.filter(
        product_store=product_store_obj,
        programming_invoice__subsidiary_store_origin=subsidiary_store_origin_obj,
        programming_invoice__subsidiary_store_destiny=subsidiary_store_destiny_obj)

    k_initial_set = query_set.filter(operation='C')
    if k_initial_set.count() > 0:
        k_initial_quantity = k_initial_set.first().remaining_quantity

    k_inputs_set = query_set.filter(operation='E', id__lte=k_id + 1).values('product_store').annotate(
        total=Sum('quantity'))
    if k_inputs_set.count() > 0:
        k_inputs_quantity = k_inputs_set[0].get('total')

    return k_initial_quantity + k_inputs_quantity


def get_kardex_dictionary(my_subsidiary_obj, is_pdf=False, start_date=None, end_date=None):
    my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(
        subsidiary=my_subsidiary_obj, category='G')  # pluspetrol

    my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(
        subsidiary=my_subsidiary_obj, category='I')  # tu almacen insumos

    product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')

    product_store_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)

    my_product_store_supply_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_insume_obj,
                                                           product=product_obj)

    dictionary = []
    merge_scope = None
    total_charge = 0
    summary = 0
    my_remaining_quantity = 0
    other_remaining_quantity = 0
    _total_quantity = 0
    _total_travel = 0
    _total_expenses = 0
    total_sum_charge = 0
    total_plus_petrol = 0
    for k in Kardex.objects.filter(product_store=product_store_obj).filter(Q(
            programming_invoice__date_arrive__range=(start_date, end_date)) | Q(
        requirement_detail__requirement_buys__approval_date__range=(start_date, end_date))).order_by('create_at'):
        # filter(requirement_detail__requirement_buys__approval_date__range=(start_date, end_date)).order_by('create_at'):
        total_plus_petrol = k.remaining_quantity
        new = {
            'id': k.id,
            'programming_invoice': k.operation,
            'requirement_detail': k.product_store.id,
            'date': k.create_at,
            'inputs': [],
            'outputs': [],
            'initial': [],
            'remaining_quantity': k.remaining_quantity,
        }

        if k.programming_invoice is not None:
            if k.programming_invoice.subsidiary_store_destiny == my_subsidiary_store_insume_obj:
                my_remaining_quantity = sum_inputs_from_subsidiary_store_supplies(
                    k.id,
                    my_product_store_supply_obj,
                    my_subsidiary_store_glp_obj,
                    my_subsidiary_store_insume_obj,
                )

        if k.requirement_detail is not None:  # entradas a pluspetrol

            programming_invoice = {
                'type': '-',
                'quantity': '0',
                'my_charge': '0',
                'other_charge': '0',
                'total_charge': '0',
                'id_programing': '0',
                'cash_flow': '-',
                'owner': '-',
                'license_plate': '-',
                'subsidiary': '-',
                'invoices': '-',
                'number_scop': '-',
                'date_programming': '-',
                'summary': summary,
                'my_remaining_quantity': my_remaining_quantity,
                'other_remaining_quantity': other_remaining_quantity,
            }
            new.get('outputs').append(programming_invoice)

            rd = k.requirement_detail
            _total_quantity = _total_quantity + rd.quantity
            requirement_detail = {
                'type': 'Compra',
                'quantity': rd.quantity,
                'invoice': rd.requirement_buys.invoice,
                'date': rd.requirement_buys.approval_date,
                'programmings': [],
            }

            new.get('inputs').append(requirement_detail)

            dictionary.append(new)

        else:

            requirement_detail = {
                'type': '-',
                'quantity': '0',
                'invoice': '-',
                'programmings': '-'
            }
            new.get('inputs').append(requirement_detail)

            if k.programming_invoice is not None:  # salida en pluspetrol y entrada en otro almacen

                pi = k.programming_invoice
                invoices = []

                for p in Requirement_buys.objects.filter(
                        programminginvoice__requirementBuysProgramming__id=pi.requirementBuysProgramming.id):
                    i = {
                        'id': p.id,
                        'invoice': p.invoice,
                        'quantity_invoice': p.programminginvoice_set.filter(
                            requirementBuysProgramming__id=pi.requirementBuysProgramming.id,
                            requirement_buys_id=p.id).first().quantity
                    }
                    invoices.append(i)
                # gastos de comustible
                expenses = []
                expenses_set = ProgrammingExpense.objects.filter(
                    requirementBuysProgramming__id=pi.requirementBuysProgramming.id)
                for es in expenses_set:
                    e = {
                        'id': es.id,
                        'invoice': es.invoice,
                        'date': es.date_invoice,
                        'type': es.get_type_display(),
                        'price': es.price,
                        # 'total': es.price * es.quantity,
                    }
                    expenses.append(e)
                    _total_expenses = _total_expenses + es.price

                my_charge = 0
                other_charge = 0

                charge_set = Programminginvoice.objects.filter(
                    requirementBuysProgramming_id=pi.requirementBuysProgramming.id,
                    subsidiary_store_origin=my_subsidiary_store_glp_obj)

                my_charge_set = charge_set.filter(
                    subsidiary_store_destiny=my_subsidiary_store_insume_obj). \
                    values('requirementBuysProgramming').annotate(totals=Sum('quantity'))
                if my_charge_set.count() > 0:
                    my_charge = my_charge_set[0].get('totals')
                    total_charge = total_charge + my_charge
                    total_sum_charge = total_sum_charge + my_charge

                if merge_scope == pi.requirementBuysProgramming.number_scop:
                    dictionary.pop(len(dictionary) - 1)
                    total_charge = total_charge - other_charge - my_charge
                    _total_travel = _total_travel - 1
                    total_sum_charge = total_sum_charge - my_charge - other_charge
                _total_travel = _total_travel + 1

                cash = []
                cash_set = CashFlow.objects.filter(requirement_programming=pi.requirementBuysProgramming.id)
                for c in cash_set:
                    cs = {
                        'id': c.id,
                        'date_transaction': c.transaction_date,
                        'mount': c.total,
                        'code_operation': c.operation_code,
                        'description': c.description,
                    }
                    cash.append(cs)
                programming_invoice = {
                    'type': 'Entrada' + "-" + str(_total_travel),
                    'quantity': pi.calculate_total_programming_quantity(),
                    'my_charge': my_charge,
                    'other_charge': other_charge,
                    'total_charge': total_charge,
                    'id_programing': pi.id,
                    'cash_flow': cash,
                    'owner': pi.requirementBuysProgramming.truck.owner,
                    'license_plate': pi.requirementBuysProgramming.truck.license_plate,
                    'subsidiary': pi.subsidiary_store_destiny.subsidiary.name,
                    'invoices': invoices,
                    'number_scop': pi.requirementBuysProgramming.number_scop,
                    'expenses': expenses,
                    'date_programming': pi.date_arrive,
                    'summary': summary,
                    'my_remaining_quantity': my_remaining_quantity,
                    'other_remaining_quantity': other_remaining_quantity,
                }
                merge_scope = pi.requirementBuysProgramming.number_scop
                new.get('outputs').append(programming_invoice)

                dictionary.append(new)

            else:  # kardex inicial en pluspetrol
                programming_invoice = {
                    'type': '-',
                    'quantity': '0',
                    'license_plate': '-',
                    'subsidiary': '-',
                    'invoices': '-',
                    'number_scop': '-',
                    'date_programming': '-',
                    'summary': summary,
                    'my_remaining_quantity': my_remaining_quantity,
                    'other_remaining_quantity': other_remaining_quantity,
                }
                new.get('outputs').append(programming_invoice)

                initial = {
                    'type': 'Inicio',
                    'quantity': k.remaining_quantity
                }
                new.get('initial').append(initial)

                dictionary.append(new)

    tpl = loader.get_template('buys/report_kardex_dictionary.html')
    context = ({
        'dictionary': dictionary,
        'is_pdf': is_pdf,
        'start_date': start_date,
        'end_date': end_date,
        'total_input': _total_quantity,
        'total_travel': _total_travel,
        'total_expenses': _total_expenses,
        'total_sum_charge': total_sum_charge,
        'total_plus_petrol': total_plus_petrol,
    })

    return tpl.render(context)
    # return render(request, 'buys/report_kardex_dictionary.html', {'dictionary': dictionary}) //un template renderizado


# Actualizar estado de la compra
def update_state_annular_purchase(request):
    if request.method == 'GET':
        id_purchase = request.GET.get('pk', '')
        purchase_obj = Purchase.objects.get(pk=int(id_purchase))
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


def get_details_by_purchase(request):
    if request.method == 'GET':
        purchase_id = request.GET.get('ip', '')
        purchase_obj = Purchase.objects.get(pk=int(purchase_id))
        details_purchase = PurchaseDetail.objects.filter(purchase=purchase_obj)
        t = loader.get_template('buys/table_details_purchase_by_purchase.html')
        c = ({
            'details': details_purchase,
        })
        return JsonResponse({
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)


def get_requirements_buys_list_approved(request):
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
            requirements_buys = Requirement_buys.objects.filter(subsidiary__id=subsidiary_obj.id,
                                                                status='2',
                                                                approval_date__range=(
                                                                    date_initial, date_final)).distinct('id')

            requirements_details_total_quantity = RequirementDetail_buys.objects.filter(
                requirement_buys__approval_date__range=(date_initial, date_final), requirement_buys__status='2',
                requirement_buys__subsidiary=subsidiary_obj).aggregate(Sum('quantity'))

            requirements_details_total_amount = RequirementDetail_buys.objects.filter(
                requirement_buys__approval_date__range=(date_initial, date_final), requirement_buys__status='2',
                requirement_buys__subsidiary=subsidiary_obj).aggregate(Sum('amount'))

            requirements_details_total_amount_pen = RequirementDetail_buys.objects.filter(
                requirement_buys__approval_date__range=(date_initial, date_final), requirement_buys__status='2',
                requirement_buys__subsidiary=subsidiary_obj).aggregate(Sum('amount_pen'))

            tpl = loader.get_template('buys/requirements_buys_approved_grid_list.html')
            context = ({
                'requirements': requirements_buys,
                'total_quantity': requirements_details_total_quantity['quantity__sum'],
                'total_amount_pen': requirements_details_total_amount_pen['amount_pen__sum'],
                'total_amount': requirements_details_total_amount['amount__sum'],
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
            })
        else:
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            return render(request, 'buys/requirements_buys_approved_list.html', {
                # 'purchases_store': purchases_store,
                'date_now': date_now,
            })


def create_requirement_view(request):
    my_date = datetime.now()
    date_now = my_date.strftime("%Y-%m-%d")
    supplier_set = Supplier.objects.all()
    unit_set = Unit.objects.all()
    product_set = Product.objects.filter(is_approved_by_osinergmin=True)
    t = loader.get_template('buys/requirement_glp.html')
    c = ({
        'supplier_set': supplier_set,
        'unit_set': unit_set,
        'product_set': product_set,
        'date_now': date_now,
    })
    return JsonResponse({
        'form': t.render(c, request),
    })


@csrf_exempt
def save_requirement(request):
    if request.method == 'POST':
        _date = request.POST.get('date-requirement', '')
        _scop = request.POST.get('scop', '')
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        _product = request.POST.get('product', '')
        product_obj = Product.objects.get(id=int(_product))
        _unit = request.POST.get('units', '')
        unit_obj = Unit.objects.get(id=int(_unit))
        _quantity = decimal.Decimal(request.POST.get('quantity', 0))

        requirement_buy_obj = Requirement_buys(
            creation_date=_date,
            number_scop=_scop,
            user=user_obj,
            subsidiary=subsidiary_obj
        )
        requirement_buy_obj.save()

        new_detail_requirement_buy = {
            'product': product_obj,
            'requirement_buys': requirement_buy_obj,
            'quantity': _quantity,
            'unit': unit_obj,
        }
        new_detail_requirement_buy = RequirementDetail_buys.objects.create(**new_detail_requirement_buy)
        new_detail_requirement_buy.save()

        return JsonResponse({
            'message': 'Requerimiento registrado correctamente.',
            'requirement_buy': requirement_buy_obj.id,
        }, status=HTTPStatus.OK)


def get_modal_payment_buys_approved(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        requirement_id = int(request.GET.get('requirement_id', ''))
        requirement_buys_obj = Requirement_buys.objects.get(id=requirement_id)
        requirementdetail_buys_obj = RequirementDetail_buys.objects.get(requirement_buys=requirement_buys_obj)
        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        tpl = loader.get_template('buys/new_payment_from_buys.html')
        context = ({
            'choices_payments': TransactionPayment._meta.get_field('type').choices,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'date': formatdate,
            'requirement_id': requirement_id,
            'invoice': requirement_buys_obj.invoice,
            'status_pay': requirement_buys_obj.status_pay,
            'amount_dollar': requirementdetail_buys_obj.amount,
            'amount_sol': requirementdetail_buys_obj.amount_pen,
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_loan_payment_buys_approved(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        requirement_id = int(request.POST.get('requirement_id', ''))
        requirement_buys_obj = Requirement_buys.objects.get(id=requirement_id)
        requirement_details_buys_obj = RequirementDetail_buys.objects.filter(requirement_buys=requirement_buys_obj,
                                                                             product__id=4).last()
        payment = request.POST.get('loan_payment', '')
        transaction_payment_type = str(request.POST.get('transaction_payment_type'))
        _operation_date = request.POST.get('date_return_loan0', '')
        cash_obj = None
        cash_flow_date = ''
        cash_flow_type = ''
        cash_flow_description = ''
        code_operation = str(request.POST.get('code_operation'))

        if transaction_payment_type == 'D':
            cash_flow_description = str(request.POST.get('description_deposit'))
            cash_flow_type = 'R'
            cash_flow_date = str(request.POST.get('id_date_deposit'))
            cash_id = str(request.POST.get('id_cash_deposit'))
            cash_obj = Cash.objects.get(id=cash_id)

        elif transaction_payment_type == 'E':
            cash_flow_date = str(request.POST.get('id_date'))
            cash_flow_description = str(request.POST.get('id_description'))
            cash_flow_type = 'S'
            cash_id = str(request.POST.get('id_cash_efectivo'))
            cashflow_set = CashFlow.objects.filter(cash_id=cash_id,
                                                   transaction_date__date=cash_flow_date, type='A')
            if cashflow_set.count() > 0:
                cash_obj = cashflow_set.first().cash
            else:
                data = {'error': "No existe una Apertura de Caja, Favor de revisar las Control de Cajas"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        save_loan_payment_in_cash_flow(
            cash_obj=cash_obj,
            user_obj=user_obj,
            requirement_buys_obj=requirement_buys_obj,
            cash_flow_date=cash_flow_date,
            cash_flow_type=cash_flow_type,
            cash_flow_operation_code=code_operation,
            cash_flow_total=payment,
            cash_flow_description=cash_flow_description,
            loan_payment_quantity=requirement_details_buys_obj.quantity,
            loan_payment_type='C',
            loan_payment_operation_date=_operation_date,
            transaction_payment_type=transaction_payment_type,
            requirement_detail_buys_obj=requirement_details_buys_obj,
        )
        if requirement_buys_obj.debt() == 0:
            requirement_buys_obj.status_pay = '2'
            requirement_buys_obj.save()
        return JsonResponse({
            'success': True,
            'message': 'El cliente se asocio correctamente.',
            # 'grid': get_dict_orders(order_set, client_obj=client_obj, is_pdf=False),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_programming_pay(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        programming_invoice_id = request.GET.get('programming_id', '')
        start_date = request.GET.get('start-date', '')
        end_date = request.GET.get('end-date', '')
        programming_invoice_obj = Programminginvoice.objects.get(id=int(programming_invoice_id))
        requirement_programming_obj = RequirementBuysProgramming.objects.get(
            id=programming_invoice_obj.requirementBuysProgramming.id)
        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='104')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        tpl = loader.get_template('buys/new_payment_programming.html')
        context = ({
            'choices_payments': TransactionPayment._meta.get_field('type').choices,
            'requirement_programming': requirement_programming_obj,
            'programming_invoice': programming_invoice_obj,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'date': formatdate,
            'start_date': start_date,
            'end_date': end_date
        })

        return JsonResponse({
            'grid': tpl.render(context, request),

        }, status=HTTPStatus.OK)


def new_payment_programming_glp(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        purchase_total = str(request.POST.get('purchase_total'))
        purchase_pay = decimal.Decimal(request.POST.get('purchase_pay'))
        start_date = str(request.POST.get('date-ini'))
        end_date = str(request.POST.get('date-fin'))
        transaction_payment_type = str(request.POST.get('transaction_payment_type'))
        requirement_programming_id = int(request.POST.get('requirement_programming'))
        requirement_programming_obj = RequirementBuysProgramming.objects.get(id=requirement_programming_id)
        purchases_set = Purchase.objects.filter(purchase_date__range=[start_date, end_date], subsidiary=subsidiary_obj,
                                                status='A')

        date_converter = ''
        cash_flow_date = str(request.POST.get('id_date'))
        cash_flow_transact_date_deposit = str(request.POST.get('id_date_deposit'))
        date_converter = datetime.strptime(cash_flow_transact_date_deposit, '%Y-%m-%d').date()
        formatdate = date_converter.strftime("%d-%m-%y")

        if transaction_payment_type == 'E':
            cash_id = str(request.POST.get('cash_efectivo'))
            cash_obj = Cash.objects.get(id=cash_id)
            cash_flow_description = str(request.POST.get('description_cash'))
            # cash_flow_date = str(request.POST.get('id_date'))

            cashflow_obj = CashFlow(
                transaction_date=cash_flow_date,
                description=cash_flow_description,
                document_type_attached='O',
                type='S',
                total=purchase_pay,
                cash=cash_obj,
                user=user_obj,
                requirement_programming=requirement_programming_obj,
            )
            cashflow_obj.save()

        if transaction_payment_type == 'D':
            cash_flow_description = str(request.POST.get('description_deposit'))
            # cash_flow_transact_date_deposit = str(request.POST.get('id_date_deposit'))
            cash_id = str(request.POST.get('id_cash_deposit'))
            cash_obj = Cash.objects.get(id=cash_id)
            code_operation = str(request.POST.get('code_operation'))

            cashflow_obj = CashFlow(
                transaction_date=cash_flow_transact_date_deposit,
                document_type_attached='O',
                description=cash_flow_description,
                type='R',
                operation_code=code_operation,
                total=purchase_pay,
                cash=cash_obj,
                user=user_obj,
                requirement_programming=requirement_programming_obj,
            )
            cashflow_obj.save()

        return JsonResponse({
            'message': 'Pago registrado con exito.',
            'pk': requirement_programming_obj.id,
            # 'grid': get_dict_purchases(purchases_set),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_programming_payment_table(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        pk = request.GET.get('programming_id', '')
        # programming_invoice_id = request.GET.get('programming_id', '')
        # programming_invoice_obj = Programminginvoice.objects.get(id=int(programming_invoice_id))
        requirement_programming_obj = RequirementBuysProgramming.objects.get(
            id=int(pk))
        cash_flow_set = CashFlow.objects.filter(requirement_programming=requirement_programming_obj)
        tpl = loader.get_template('buys/table_list_payment_programming.html')
        context = ({
            'cash_flow_set': cash_flow_set,
        })

        return JsonResponse({
            'grid': tpl.render(context, request),

        }, status=HTTPStatus.OK)


def get_programmings_by_dates(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        subsidiary_set = Subsidiary.objects.all()

        return render(request, 'buys/report_programmings_all.html', {
            'formatdate': formatdate,
            'subsidiary_set': subsidiary_set
        })

    elif request.method == 'POST':
        date_initial = str(request.POST.get('date_initial'))
        date_final = str(request.POST.get('date_final'))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        if date_initial == date_final:
            requirement_programming_set = RequirementBuysProgramming.objects.filter(
                programminginvoice__requirement_buys__subsidiary=subsidiary_obj, status='F',
                programminginvoice__date_arrive=date_initial).distinct('number_scop')
        else:
            requirement_programming_set = RequirementBuysProgramming.objects.filter(
                programminginvoice__requirement_buys__subsidiary=subsidiary_obj, status='F',
                programminginvoice__date_arrive__range=(date_initial, date_final)).distinct('number_scop')

        return JsonResponse({
            'grid': get_dict_programming_queries(requirement_programming_set),
        }, status=HTTPStatus.OK)


def get_dict_programming_queries(requirement_programming_set):
    count = 0
    truck_dict = {}
    for r in requirement_programming_set:
        _search_value = r.truck.id
        if _search_value in truck_dict.keys():
            _truck = truck_dict[_search_value]
            _expenses = _truck.get('expenses')
            truck_dict[_search_value]['expenses'] = _expenses + r.calculate_total_programming_expenses_price()
            _count = _truck.get('count')
            truck_dict[_search_value]['count'] = _count + 1
            _quantity_total = _truck.get('quantity_total')
            truck_dict[_search_value][
                'quantity_total'] = _quantity_total + r.programminginvoice_set.last().calculate_total_programming_quantity()
        else:
            truck_dict[_search_value] = {'pk': _search_value, 'license_plate': r.truck.license_plate, 'count': 1,
                                         'quantity_total': r.programminginvoice_set.last().calculate_total_programming_quantity(),
                                         'expenses': r.calculate_total_programming_expenses_price()}

    tpl = loader.get_template('buys/report_programming_grid_all.html')
    context = ({
        'dictionary': truck_dict,
        'count': count,
    })
    return tpl.render(context)


def get_report_graphic_glp(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        if pk != '':
            dates_request = request.GET.get('dates', '')
            data_dates = json.loads(dates_request)
            date_initial = (data_dates["date_initial"])
            date_final = (data_dates["date_final"])
            quantity_date = []
            amount_date = []
            amount_payment = []
            for r in RequirementDetail_buys.objects.filter(
                    requirement_buys__approval_date__range=(date_initial, date_final)):
                data_quantity = {
                    'label': str(r.requirement_buys.approval_date.strftime("%d-%m-%Y")),
                    'y': float(round(r.quantity, 2))
                }
                quantity_date.append(data_quantity)
                data_amount = {
                    'label': str(r.requirement_buys.approval_date.strftime("%d-%m-%Y")),
                    'y': float(round(r.amount_pen, 2))
                }
                amount_date.append(data_amount)
                try:
                    p = CashFlow.objects.filter(requirement_buys_id=r.requirement_buys.id).values('total').last()
                    if p is None:
                        totals = 0
                    else:
                        totals = p['total']

                except CashFlow.DoesNotExist:
                    totals = 0
                data_payment = {
                    'label': str(r.requirement_buys.approval_date.strftime("%d-%m-%Y")),
                    'y': float(round(totals * r.change_coin, 2))
                }
                amount_payment.append(data_payment)

            tpl = loader.get_template('buys/report_graphic_glp_by_dates.html')
            context = ({
                'quantity_d': quantity_date,
                'amount_d': amount_date,
            })
            tpl1 = loader.get_template('buys/report_graphic_glp_by_dates1.html')
            context1 = ({
                'quantity_d': quantity_date,
                'amount_payment': amount_payment
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
                'forms': tpl1.render(context1, request),
            })
        else:
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            return render(request, 'buys/report_graphic_glp.html', {
                'date_now': date_now,
            })


def report_purchases_all(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    truck_set = Truck.objects.all().order_by('license_plate')
    truck_set2 = Purchase.objects.filter(subsidiary=subsidiary_obj,
                                         truck__isnull=False).distinct('truck__license_plate').values('truck__id',
                                                                                                      'truck__license_plate').order_by('truck__license_plate')
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


def get_purchases_by_license_plate(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    truck_id = request.GET.get('truck_id', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        return render(request, 'buys/report_purchases_by_supplier.html', {
            'formatdate': formatdate,
        })


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
            purchase__status='A',purchase__purchase_date__range=[start_date, end_date]).values(
            'purchase__supplier__name',
            'purchase__supplier__business_name',
            'purchase__supplier__sector',
            'purchase__supplier__id').exclude(purchase__supplier__id__in=[1, 363, 364, 369]).annotate(total=Sum(F('price_unit') * F('quantity'))).order_by('-total')

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
                                                            purchase__purchase_date__range=[start_date, end_date]).values('purchase__supplier__id', 'purchase__supplier__name', 'purchase__supplier__business_name').exclude(purchase__supplier__id__in=[1, 363, 364, 369]).annotate(total=Sum(F('price_unit') * F('quantity'))).order_by('-total')

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




