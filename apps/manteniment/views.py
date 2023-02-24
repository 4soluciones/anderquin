from django.shortcuts import render
from django.views.generic import TemplateView, View, CreateView, UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from http import HTTPStatus
from .models import *
from apps.hrm.models import Subsidiary, Worker, Establishment
from django.template import loader
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user
from apps.sales.views import kardex_input, kardex_ouput, kardex_initial, calculate_minimum_unit
import json
import decimal
from datetime import datetime
from ..sales.models import Product, Unit, Supplier, SubsidiaryStore, ProductStore, ProductDetail, Kardex
from django.core import serializers


class Home(TemplateView):
    template_name = 'buys/home.html'


def purchase_form(request):
    # form_obj = FormGuide()
    # programmings = Programming.objects.filter(status__in=['P']).order_by('id')
    supplier_obj = Supplier.objects.all()
    product_obj = Product.objects.all()
    unitmeasurement_obj = Unit.objects.all()
    return render(request, 'buys/purchase_form.html', {
        # 'form': form_obj,
        'supplier_obj': supplier_obj,
        'unitmeasurement_obj': unitmeasurement_obj,
        'product_obj': product_obj,
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
        date = str(data_purchase["Date"])
        invoice = str(data_purchase["Invoice"])

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
            subsidiary=subsidiary_obj
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
        purchase_obj = Purchase.objects.get(id=int(purchase_id))
        # CONSULTA SI LA COMPRA YA ESTA EN ALMACEN Y ROMPE LA SECUENCIA
        if purchase_obj.status == 'A':
            data = {'error': 'LOS PRODUCTOS YA ESTAN ASIGNADOS A SU ALMACEN.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        try:
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='M')
        except SubsidiaryStore.DoesNotExist:
            data = {'error': 'No existe almacen de mercaderia.'}
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
            'message': 'ALLMACENADO',

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

    }, status=HTTPStatus.OK)


def get_requeriments_buys_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    requiriments_buys = Requirement_buys.objects.filter(subsidiary__id=subsidiary_obj.id).order_by("creation_date")
    return render(request, 'buys/requirement_buy_list.html', {
        'requiriments_buys': requiriments_buys
    })


def get_purchase_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    purchases = Purchase.objects.filter(subsidiary=subsidiary_obj)
    return render(request, 'buys/purchase_list.html', {
        'purchases': purchases
    })


def get_detail_purchase_store(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        purchase_obj = Purchase.objects.get(id=pk)
        purchase_details = PurchaseDetail.objects.filter(purchase=purchase_obj)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_stores = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj)
        t = loader.get_template('buys/assignment_detail_purchase.html')
        c = ({
            'purchase': purchase_obj,
            'detail_purchase': purchase_details,
            'subsidiary_stores': subsidiary_stores,
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
        # pk = request.GET.get('pk', '')
        # requirement_buy_obj = Requirement_buys.objects.get(id=pk)
        programmign_buy_obj = RequirementBuysProgramming.objects.filter(status='P')
        requirement_buys = Requirement_buys.objects.filter(status=2)
        # subsidiary_obj = Subsidiary.objects.all()
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
                    'subsidiary_store': other_subsidiary_store_obj,
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
                kardex_ouput(my_product_store.id, quantity_minimum_unit, new_programming_invoice_obj)
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

        data = {'error': 'LOS TANQUEOS YA SE REGISTRARON.'}
        response = JsonResponse(data)
        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


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
            requirement_detail_obj = RequirementDetail_buys.objects.get(id=requirement_detail_id)
            requirement_detail_obj.price = _price
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
    requirements_obj = Requirement_buys.objects.all().filter(status=2, subsidiary__id=subsidiary_obj.id)
    return render(request, 'buys/requirement_balance.html', {
        'requirements': requirements_obj,
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
            # requirementprogramming_obj = RequirementBuysProgramming.objects.filter(truck=truck_obj, status='F')
            requirementprogramming_obj = RequirementBuysProgramming.objects.filter(
                programminginvoice__requirement_buys__subsidiary=subsidiary_obj, truck=truck_obj, status='F',
                programminginvoice__date_arrive__range=(date_initial, date_final)).distinct('number_scop')
            # programminginvoice_obj = Programminginvoice.objects.filter(requirementBuysProgramming=requirementprogramming_obj)

            tpl = loader.get_template('buys/report_programming_by_truck_and_dates_grid.html')
            context = ({
                # 'programmingsinvoice': programminginvoice_obj,
                'programmings': requirementprogramming_obj,
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


def get_report_kardex_glp(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        pk = request.GET.get('subsidiary_store_id', '')
        if pk != '':
            return JsonResponse({
                'success': True,
                'grid': get_report_context_kardex_glp(subsidiary_obj, pk),
            }, status=HTTPStatus.OK)
        else:
            subsidiary_store_set = SubsidiaryStore.objects.exclude(subsidiary=subsidiary_obj).filter(category='I')
            mydate = datetime.now()
            formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
            return render(request, 'buys/report_kardex_glp.html', {
                'subsidiary_stores': subsidiary_store_set,
                'date': formatdate
            })


def get_report_kardex_glp_grid(request, pk):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    return render(request, 'buys/report_kardex_glp_grid.html',
                  get_report_context_kardex_glp(subsidiary_obj, pk, get_context=True))
