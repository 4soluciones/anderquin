import pytz
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.views.generic import TemplateView, View, CreateView, UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponse
from http import HTTPStatus
from .format_dates import validate
from django.db.models import Q
from .models import *
from .forms import *
from apps.hrm.models import Subsidiary, District, DocumentType, Employee, Worker
from apps.comercial.models import DistributionMobil, Truck, DistributionDetail, ClientAdvancement, ClientProduct, \
    Programming, Route, Guide, GuideDetail
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user, get_sales_vs_expenses, get_subsidiary_by_user_id
from apps.accounting.views import TransactionAccount, LedgerEntry, get_account_cash, Cash, CashFlow, AccountingAccount
import json
import decimal
import math
import random

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import ImageFieldFile
from django.template import loader
from datetime import datetime, timedelta
from django.db import DatabaseError, IntegrityError
from django.core import serializers
from apps.sales.views_SUNAT import send_bill_nubefact, send_receipt_nubefact
from apps.sales.number_to_letters import numero_a_letras, numero_a_moneda
from django.utils import timezone
from django.db.models import Min, Sum, Max, Q, F, Prefetch, Subquery, OuterRef, Value
from django.db.models.functions import Greatest
from django.db.models.functions import (
    ExtractDay, ExtractMonth, ExtractQuarter, ExtractWeek,
    ExtractWeekDay, ExtractIsoYear, ExtractYear,
)

from ..buys.models import PurchaseDetail, Purchase, RequirementDetail_buys, Programminginvoice
from apps.sales.funtions import *


class Home(TemplateView):
    template_name = 'sales/home.html'


class ProductList(View):
    model = Product
    form_class = FormProduct
    template_name = 'sales/product_list.html'

    def get_queryset(self):
        last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]

        return self.model.objects.filter(
            is_enabled=True
        ).select_related('product_family', 'product_brand', 'product_subcategory__product_category').prefetch_related(
            Prefetch(
                'productstore_set', queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                    .annotate(
                    last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                )
                # .annotate(
                #     last_kardex=Subquery(
                #         Kardex.objects.filter(product_store=OuterRef('id'), id='last_id').values('remaining_quantity')[:1], output_field=models.DecimalField()
                #     )
                # )
            ),
            Prefetch(
                'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
            ),
            Prefetch(
                'recipes', queryset=ProductRecipe.objects.select_related('unit').select_related('product_input')
            )
        ).order_by('id')

    def get_context_data(self, **kwargs):
        user = self.request.user.id
        # user_obj = User.objects.get(id=int(user))
        # subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_obj = get_subsidiary_by_user_id(user)
        context = {
            'products': self.get_queryset(),
            'subsidiary': subsidiary_obj,
            'form': self.form_class
        }
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class JsonProductList(View):
    def get(self, request):
        products = Product.objects.filter(is_enabled=True)
        user = self.request.user.id
        user_obj = User.objects.get(id=int(user))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        t = loader.get_template('sales/product_grid_list.html')
        c = ({'products': products, 'subsidiary': subsidiary_obj})
        return JsonResponse({'result': t.render(c)})


class JsonProductCreate(CreateView):
    model = Product
    form_class = FormProduct
    template_name = 'sales/product_create.html'

    def post(self, request):
        data = dict()
        form = FormProduct(request.POST, request.FILES)

        if form.is_valid():
            print('isvalid()')
            product = form.save()
            # converting a database model to a dictionary...
            data['product'] = model_to_dict(product)
            # Encode into JSON formatted Data
            result = json.dumps(data, cls=ExtendedEncoder)
            # Para pasar cualquier otro objeto serializable JSON, debe establecer el parámetro seguro en False.
            response = JsonResponse(result, safe=False)
            # change status code in JsonResponse
            response.status_code = HTTPStatus.OK
        else:
            # use form.errors to add the error msg as a dictonary
            data['error'] = "form not valid!"
            data['form_invalid'] = form.errors
            # Por defecto, el primer parámetro de JsonResponse, debe ser una instancia dict.
            # Para pasar cualquier otro objeto serializable JSON, debe establecer el parámetro seguro en False.
            response = JsonResponse(data)
            # change status code in JsonResponse
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


class JsonProductUpdate(UpdateView):
    model = Product
    form_class = FormProduct
    template_name = 'sales/product_update.html'

    def post(self, request, pk):
        data = dict()
        product = self.model.objects.get(pk=pk)
        # form = SnapForm(request.POST, request.FILES, instance=instance)
        form = self.form_class(instance=product, data=request.POST, files=request.FILES)
        if form.is_valid():
            product = form.save()
            data['product'] = model_to_dict(product)
            result = json.dumps(data, cls=ExtendedEncoder)
            response = JsonResponse(result, safe=False)
            response.status_code = HTTPStatus.OK
        else:
            data['error'] = "form not valid!"
            data['form_invalid'] = form.errors
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


def get_product(request):
    data = dict()
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product_obj = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        subsidiaries = Subsidiary.objects.all()
        inventories = Kardex.objects.filter(product_store__product_id=pk)
        units = Unit.objects.all()
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        unit_min_obj = None
        product_detail = ProductDetail.objects.filter(
            product=product_obj).annotate(Min('quantity_minimum'))

        if product_detail.count() > 0:
            unit_min_obj = product_detail.first().unit

        t = loader.get_template('sales/product_update_quantity_on_hand.html')
        c = ({'product': product_obj,
              'subsidiaries': subsidiaries,
              'inventories': inventories,
              'units': units,
              'unit_min': unit_min_obj,
              'own_subsidiary': subsidiary_obj,
              })

        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def new_quantity_on_hand(request):
    if request.method == 'GET':
        store_request = request.GET.get('stores', '')
        data = json.loads(store_request)

        product_id = str(data['Product'])
        product = Product.objects.get(pk=int(product_id))

        for detail in data['Details']:
            if detail['Operation'] == 'create':
                subsidiary_store_id = str(detail['SubsidiaryStore'])
                subsidiary_store = SubsidiaryStore.objects.get(pk=int(subsidiary_store_id))

                new_stock = 0
                new_price_unit = 0

                if detail['Quantity']:
                    new_stock = decimal.Decimal(detail['Quantity'])

                    if detail['Price']:
                        new_price_unit = decimal.Decimal(detail['Price'])

                        if detail['Unit'] != '0':
                            unit_obj = Unit.objects.get(id=int(detail['Unit']))

                            search_product_detail_set = ProductDetail.objects.filter(
                                unit=unit_obj, product=product)

                            if search_product_detail_set.count == 0:
                                product_detail_obj = ProductDetail(
                                    product=product,
                                    price_sale=new_price_unit,
                                    unit=unit_obj,
                                    quantity_minimum=1
                                )
                                product_detail_obj.save()
                        # New product store
                        new_product_store = {
                            'product': product,
                            'subsidiary_store': subsidiary_store,
                            'stock': new_stock
                        }
                        product_store_obj = ProductStore.objects.create(**new_product_store)
                        product_store_obj.save()

                        kardex_initial(product_store_obj, new_stock, new_price_unit)

                    else:
                        data = {'error': "Precio no existe!"}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response
            # else:
            #     data = {'error': "Producto con inventario inicial ya registrado!"}
            #     response = JsonResponse(data)
            #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            #     return response
        return JsonResponse({
            'success': True,
        })


def get_recipe_by_product(request):
    if request.method == 'GET':
        store_request = request.GET.get('stores', '')
        data = json.loads(store_request)

        product_id = str(data['Product'])
        product = Product.objects.get(pk=int(product_id))

        for detail in data['Details']:
            if detail['Operation'] == 'create':
                subsidiary_store_id = str(detail['SubsidiaryStore'])
                subsidiary_store = SubsidiaryStore.objects.get(pk=int(subsidiary_store_id))

                new_stock = 0
                new_price_unit = 0

                if detail['Quantity']:
                    new_stock = decimal.Decimal(detail['Quantity'])

                    if detail['Price']:
                        new_price_unit = decimal.Decimal(detail['Price'])

                        if detail['Unit'] != '0':
                            unit_obj = Unit.objects.get(id=int(detail['Unit']))

                            product_detail_obj = ProductDetail(
                                product=product,
                                price_sale=new_price_unit,
                                unit=unit_obj,
                                quantity_minimum=1
                            )
                            product_detail_obj.save()

                        # New product store
                        new_product_store = {
                            'product': product,
                            'subsidiary_store': subsidiary_store,
                            'stock': new_stock
                        }
                        product_store_obj = ProductStore.objects.create(**new_product_store)
                        product_store_obj.save()

                        kardex_initial(product_store_obj, new_stock, new_price_unit)

                    else:
                        data = {'error': "Precio no existe!"}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response
            else:
                data = {'error': "Producto con inventario inicial ya registrado!"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
        return JsonResponse({
            'success': True,
        })


def get_kardex_by_product(request):
    data = dict()
    mydate = datetime.now()
    formatdate = mydate.strftime("%Y-%m-%d")
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        products = Product.objects.all()
        subsidiaries = Subsidiary.objects.all()
        subsidiaries_stores = SubsidiaryStore.objects.all()

        # check product detail
        basic_product_detail = ProductDetail.objects.filter(
            product=product, quantity_minimum=1)
        # kardex = Kardex.objects.filter(product_id=pk)
        t = loader.get_template('sales/kardex.html')
        c = ({
            'product': product,
            'subsidiaries': subsidiaries,
            'basic_product_detail': basic_product_detail,
            'subsidiaries_stores': subsidiaries_stores,
            'products': products,
            'date_now': formatdate,
        })

        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def get_list_kardex(request):
    data = dict()
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        pk_subsidiary_store = request.GET.get('subsidiary_store', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')

        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        subsidiary_store = SubsidiaryStore.objects.get(id=pk_subsidiary_store)

        try:
            product_store = ProductStore.objects.filter(
                product_id=product.id).filter(subsidiary_store_id=subsidiary_store.id)

        except ProductStore.DoesNotExist:
            data['error'] = "almacen producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        inventories = None
        if product_store.count() > 0:
            inventories = Kardex.objects.filter(
                product_store=product_store[0], create_at__date__range=[start_date, end_date]
            ).select_related(
                'product_store__product',
                'programming_invoice__requirement_buys__subsidiary',
                'requirement_detail',
                'purchase_detail',
                'manufacture_detail',
                'manufacture_recipe',
                'order_detail__order',
                'distribution_detail__distribution_mobil__truck',
                'loan_payment',
                'ball_change',
                'guide_detail__guide__programming__truck',
                'guide_detail__guide__guide_motive',
                'advance_detail__client_advancement__client',
            ).prefetch_related(
                Prefetch('programming_invoice__kardex_set',
                         queryset=Kardex.objects.select_related('product_store__subsidiary_store')),
            ).order_by('id')

        t = loader.get_template('sales/kardex_grid_list.html')
        c = ({'product': product, 'inventories': inventories})

        return JsonResponse({
            'success': True,
            'form': t.render(c),
        })


class ExtendedEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, ImageFieldFile):
            return str(o)
        else:
            return super().default(o)


class ClientList(View):
    model = Client
    form_class = FormClient
    template_name = 'sales/client_list.html'

    def get_queryset(self):
        return self.model.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['clients'] = self.get_queryset()  # agregamos la consulta al contexto
        contexto['form'] = self.form_class
        contexto['document_types'] = DocumentType.objects.all()
        contexto['districts'] = District.objects.all()
        contexto['subsidiaries'] = Subsidiary.objects.all()
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


@csrf_exempt
def new_client(request):
    data = dict()
    print(request.method)
    if request.method == 'POST':

        names = request.POST.get('names')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        email = request.POST.get('email', '')
        document_number = request.POST.get('document_number', '')
        document_type_id = request.POST.get('document_type', '')
        id_district = request.POST.get('id_district', '')
        reference = request.POST.get('reference', '')
        operation = request.POST.get('operation', '')
        client_id = int(request.POST.get('client_id', ''))  # solo se usa al editar

        if operation == 'N':

            if len(names) > 0:

                data_client = {
                    'names': names,
                    'phone': phone,
                    'email': email,
                }

                client = Client.objects.create(**data_client)
                client.save()

                if len(document_number) > 0:

                    try:
                        document_type = DocumentType.objects.get(id=document_type_id)
                    except DocumentType.DoesNotExist:
                        data['error'] = "Documento no existe!"
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response

                    data_client_type = {
                        'client': client,
                        'document_type': document_type,
                        'document_number': document_number,
                    }
                    client_type = ClientType.objects.create(**data_client_type)
                    client_type.save()

                    if len(address) > 0:

                        try:
                            district = District.objects.get(id=id_district)
                        except District.DoesNotExist:
                            data['error'] = "Distrito no existe!"
                            response = JsonResponse(data)
                            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                            return response

                        data_client_address = {
                            'client': client,
                            'address': address,
                            'district': district,
                            'reference': reference,
                        }
                        client_address = ClientAddress.objects.create(**data_client_address)
                        client_address.save()
                return JsonResponse({'success': True, 'message': 'El cliente se registro correctamente.'})
        else:

            client_obj = Client.objects.get(pk=client_id)
            client_obj.names = names
            client_obj.phone = phone
            client_obj.email = email
            client_obj.save()
            district = District.objects.get(id=id_district)
            document_type = DocumentType.objects.get(id=document_type_id)

            client_address_set = ClientAddress.objects.filter(client_id=client_id)
            if client_address_set:
                client_address_obj = client_address_set.first()

                client_address_obj.address = address
                client_address_obj.district = district
                client_address_obj.reference = reference
                client_address_obj.save()
            else:
                data_client_address = {
                    'client': client_obj,
                    'address': address,
                    'district': district,
                    'reference': reference,
                }
                client_address = ClientAddress.objects.create(**data_client_address)
                client_address.save()

            client_type_set = ClientType.objects.filter(client_id=client_id)
            if client_type_set:
                client_type_obj = client_type_set.first()
                client_type_obj.document_type = document_type
                client_type_obj.document_number = document_number
                client_type_obj.save()
            else:
                data_client_type = {
                    'client': client_obj,
                    'document_type': document_type,
                    'document_number': document_number,
                }
                client_type = ClientType.objects.create(**data_client_type)
                client_type.save()

            return JsonResponse({'success': True, 'message': 'El cliente se actualizo correctamente.'})
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def new_client_associate(request):
    data = dict()
    print(request.method)
    if request.method == 'GET':

        id = request.GET.get('client_id')
        names = request.GET.get('names')
        associates = request.GET.get('associates', '')
        _arr = []
        if associates != '[]':
            str1 = associates.replace(']', '').replace('[', '')
            _arr = str1.replace('"', '').split(",")
            client_obj = Client.objects.get(id=int(id))
            associated_set = ClientAssociate.objects.filter(client=client_obj)
            associated_set.delete()
            for a in _arr:
                subsidiary_obj = Subsidiary.objects.get(id=int(a))
                client_associate_obj = ClientAssociate(client=client_obj, subsidiary=subsidiary_obj)
                client_associate_obj.save()
        else:
            data['error'] = "Ingrese valores validos."
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        return JsonResponse({'success': True, 'message': 'El cliente se asocio correctamente.'})
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


class SalesList(View):
    template_name = 'sales/sales_list.html'

    def get_context_data(self, **kwargs):
        error = ""
        user_id = self.request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        pk = self.kwargs.get('pk', None)
        letter = self.kwargs.get('letter', None)
        contexto = {}
        if pk is not None:
            contexto['list_distribution'] = DistributionMobil.objects.get(id=int(pk))
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        # try:
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        sales_store = None
        if subsidiary_obj is None:
            error = "No tiene una sede definida."
        else:
            sales_store = SubsidiaryStore.objects.filter(
                subsidiary=subsidiary_obj, category='V').first()

        products = None
        if sales_store is None:
            error = "No tiene un almacen de ventas registrado, Favor de registrar un almacen primero."
        else:
            products = Product.objects.filter(
                is_enabled=True, productstore__subsidiary_store=sales_store
            ).prefetch_related(
                Prefetch(
                    'productstore_set', queryset=ProductStore.objects.select_related('subsidiary_store')
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                )
            ).order_by('id')
        worker_obj = Worker.objects.filter(user=user_obj).last()
        employee = Employee.objects.get(worker=worker_obj)

        client_type_set = ClientType.objects.select_related('client').filter(
            client__clientassociate__subsidiary=subsidiary_obj)
        client_dict = {}
        for ct in client_type_set:
            key = ct.client.id
            if key not in client_dict:
                client_dict[key] = {
                    'client_id': ct.client.id,
                    'client_names': ct.client.names,
                    'client_document_number': ct.document_number,
                }
        series_set = Truck.objects.all()

        contexto['employee'] = employee
        contexto['error'] = error
        contexto['sales_store'] = sales_store
        contexto['subsidiary'] = subsidiary_obj
        contexto['products'] = products
        contexto['client_dict'] = client_dict
        contexto['date'] = formatdate
        contexto['distribution'] = pk
        contexto['choices_payments'] = TransactionPayment._meta.get_field('type').choices
        contexto['electronic_invoice'] = letter
        contexto['series'] = series_set
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


def get_client(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        client_set = Client.objects.filter(id=pk)
        client_address_set = ClientAddress.objects.filter(client_id=pk)
        client_type_set = ClientType.objects.filter(client_id=pk)
        client_bill_set = OrderBill.objects.filter(order__client__id=client_set.first().id)
        client_serialized_data = serializers.serialize('json', client_set)
        client_serialized_data_address = serializers.serialize('json', client_address_set)
        client_serialized_data_type = serializers.serialize('json', client_type_set)
        client_bill = serializers.serialize('json', client_bill_set)
        client_product_set = ClientProduct.objects.filter(client=client_set.first())
        tpl = loader.get_template('sales/table_client_advancement.html')
        context = ({
            'client_product_set': client_product_set,
        })
        return JsonResponse({
            'success': True,
            'client_names': client_set.first().names,
            'client_serialized': client_serialized_data,
            'client_serialized_data_address': client_serialized_data_address,
            'client_serialized_data_type': client_serialized_data_type,
            'client_bill': client_bill,
            'grid': tpl.render(context),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


# @csrf_exempt
def set_product_detail(request):
    data = {}
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product_obj = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            data['error'] = "producto no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        products = Product.objects.all()
        units = Unit.objects.all()
        t = loader.get_template('sales/product_detail.html')
        c = ({
            'product': product_obj,
            'units': units,
            'products': products,
        })

        product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
        tpl2 = loader.get_template('sales/product_detail_grid_list.html')
        context2 = ({'product_details': product_details, })
        serialized_data = serializers.serialize('json', product_details)
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
            'grid': tpl2.render(context2),
            'serialized_data': serialized_data,
            # 'form': t.render(c),
        }, status=HTTPStatus.OK)
    else:
        if request.method == 'POST':
            id_product = request.POST.get('product', '')
            price_sale = request.POST.get('price_sale', '')
            id_unit = request.POST.get('unit', '')
            quantity_minimum = request.POST.get('quantity_minimum', '')

            if decimal.Decimal(price_sale) == 0 or decimal.Decimal(quantity_minimum) == 0:
                data['error'] = "Ingrese valores validos."
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            product_obj = Product.objects.get(id=int(id_product))
            unit_obj = Unit.objects.get(id=int(id_unit))

            try:
                product_detail_obj = ProductDetail(
                    product=product_obj,
                    price_sale=decimal.Decimal(price_sale),
                    unit=unit_obj,
                    quantity_minimum=decimal.Decimal(quantity_minimum),
                )
                product_detail_obj.save()
            except DatabaseError as e:
                data['error'] = str(e)
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            except IntegrityError as e:
                data['error'] = str(e)
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
            tpl2 = loader.get_template('sales/product_detail_grid_list.html')
            context2 = ({'product_details': product_details, })

            return JsonResponse({
                'message': 'Guardado con exito.',
                'grid': tpl2.render(context2),
            }, status=HTTPStatus.OK)


def get_product_detail(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        product_detail_obj = ProductDetail.objects.filter(id=pk)
        serialized_obj = serializers.serialize('json', product_detail_obj)
        return JsonResponse({'obj': serialized_obj}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def toogle_status_product_detail(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        text_status = request.GET.get('status', '')
        status = False
        if text_status == 'True':
            status = True
        product_detail_obj = ProductDetail.objects.get(id=pk)
        product_detail_obj.is_enabled = status
        product_detail_obj.save()

        return JsonResponse({'message': 'Cambios guardados con exito.'}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def update_product_detail(request):
    data = dict()
    if request.method == 'POST':
        id_product_detail = request.POST.get('product_detail', '')
        id_product = request.POST.get('product', '')
        price_sale = request.POST.get('price_sale', '')
        id_unit = request.POST.get('unit', '')
        quantity_minimum = request.POST.get('quantity_minimum', '')

        if decimal.Decimal(price_sale) == 0 or decimal.Decimal(quantity_minimum) == 0:
            data['error'] = "Ingrese valores validos."
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        product_obj = Product.objects.get(id=int(id_product))
        unit_obj = Unit.objects.get(id=int(id_unit))

        product_detail_obj = ProductDetail.objects.get(id=int(id_product_detail))
        product_detail_obj.quantity_minimum = quantity_minimum
        product_detail_obj.price_sale = price_sale
        product_detail_obj.product = product_obj
        product_detail_obj.unit = unit_obj
        product_detail_obj.save()

        product_details = ProductDetail.objects.filter(product=product_obj).order_by('id')
        tpl2 = loader.get_template('sales/product_detail_grid_list.html')
        context2 = ({'product_details': product_details, })

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': tpl2.render(context2),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_rate_product(request):
    if request.method == 'GET':
        id_product = request.GET.get('product', '')
        id_distribution = request.GET.get('distribution')
        distribution_obj = None
        if id_distribution != '0':
            distribution_obj = DistributionMobil.objects.get(pk=int(id_distribution))

        product_obj = Product.objects.get(id=int(id_product))
        product_details = ProductDetail.objects.filter(product=product_obj)
        subsidiaries_stores = SubsidiaryStore.objects.filter(stores__product=product_obj)
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_stores = ProductStore.objects.filter(product=product_obj, subsidiary_store__subsidiary=subsidiary_obj)
        store = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()

        serialized_obj1 = serializers.serialize('json', product_details)
        serialized_obj2 = serializers.serialize('json', product_stores)
        print(subsidiaries_stores)

        tpl = loader.get_template('sales/sales_rates.html')

        context = ({

            'store': store,
            'product_obj': product_obj,
            'subsidiaries_stores': subsidiaries_stores,
            'product_stores': product_stores,
            'product_details': product_details,
            'distribution_obj': distribution_obj,
        })

        return JsonResponse({
            'serialized_obj2': serialized_obj2,
            'grid': tpl.render(context),
        }, status=HTTPStatus.OK)


# create by Jhon por siacaso----------------------------------

def create_order_detail(request):
    if request.method == 'GET':
        sale_request = request.GET.get('sales', '')
        data_sale = json.loads(sale_request)
        distribution_obj = None
        serie_obj = None
        truck_obj = None
        client_id = str(data_sale["Client"])
        client_obj = Client.objects.get(pk=int(client_id))
        sale_total = decimal.Decimal(data_sale["SaleTotal"])
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_sales_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='V')
        # order_id = str(data_sale["Orden"])
        distribution_id = str(data_sale["Distribution"])
        serie = str(data_sale["Serie"])
        _type = str(data_sale["Type"])
        _bill_type = str(data_sale["BillType"])
        msg_sunat = ''
        sunat_pdf = ''
        _date = str(data_sale["Date"])
        is_demo = bool(int(data_sale["Demo"]))
        value_is_demo = ''
        if is_demo:
            value_is_demo = 'D'
        else:
            value_is_demo = 'P'

        if distribution_id != '0':
            distribution_obj = DistributionMobil.objects.get(pk=int(distribution_id))

        if serie != '0':
            truck_obj = Truck.objects.get(id=int(serie))
            truck_obj_id = truck_obj.id
            serie_obj = truck_obj.serial

        new_order_sale = {
            'type': _type,
            'client': client_obj,
            'user': user_obj,
            'total': sale_total,
            'distribution_mobil': distribution_obj,
            'subsidiary_store': subsidiary_store_sales_obj,
            'subsidiary': subsidiary_obj,
            'truck': truck_obj,
            'create_at': _date
            # 'correlative_sale': order_id,
        }
        order_sale_obj = Order.objects.create(**new_order_sale)
        order_sale_obj.save()
        new_detail_order = None
        for detail in data_sale['Details']:
            quantity = decimal.Decimal(detail['Quantity'])
            price = decimal.Decimal(detail['Price'])
            total = decimal.Decimal(detail['DetailTotal'])

            # recuperamos del producto
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)

            # recuperamos la unidad
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)

            item_with_unit_g = None
            item_with_unit_b = None
            new_detail_order_obj = None

            if unit_obj.name == 'BG':
                search_item_with_unit_g_set = OrderDetail.objects.filter(
                    unit__name='G', order=order_sale_obj, product=product_obj)

                if search_item_with_unit_g_set.count() > 0:
                    item_with_unit_g = search_item_with_unit_g_set.last()
                    item_with_unit_g.quantity_sold = item_with_unit_g.quantity_sold + quantity
                    item_with_unit_g.save()
                else:
                    product_detail_g = ProductDetail.objects.get(
                        product=product_obj, unit__name='G')
                    product_detail_b = ProductDetail.objects.get(
                        product=product_obj, unit__name='B')
                    new_item_with_unit_g = {
                        'order': order_sale_obj,
                        'product': product_obj,
                        'quantity_sold': quantity,
                        'price_unit': price - product_detail_b.price_sale,
                        'unit': product_detail_g.unit,
                        'status': 'V'
                    }
                    item_with_unit_g = OrderDetail.objects.create(**new_item_with_unit_g)
                    item_with_unit_g.save()

                product_detail_b = ProductDetail.objects.get(product=product_obj, unit__name='B')

                new_item_with_unit_b = {
                    'order': order_sale_obj,
                    'product': product_obj,
                    'quantity_sold': quantity,
                    'price_unit': product_detail_b.price_sale,
                    'unit': product_detail_b.unit,
                    'status': 'V'
                }
                item_with_unit_b = OrderDetail.objects.create(**new_item_with_unit_b)
                item_with_unit_b.save()
            else:
                if unit_obj.name == 'GBC':
                    search_item_with_unit_g_set_ = OrderDetail.objects.filter(
                        unit__name='GBC', order=order_sale_obj, product=product_obj)

                    if search_item_with_unit_g_set_.count() > 0:
                        item_with_unit_g_ = search_item_with_unit_g_set_.last()
                        item_with_unit_g_.quantity_sold = item_with_unit_g_.quantity_sold + quantity
                        item_with_unit_g_.save()
                    else:
                        product_detail_g = ProductDetail.objects.get(
                            product=product_obj, unit__name='GBC')
                        new_item_with_unit_g = {
                            'order': order_sale_obj,
                            'product': product_obj,
                            'quantity_sold': quantity,
                            'price_unit': price,
                            'unit': product_detail_g.unit,
                            'status': 'V'
                        }
                        item_with_unit_g = OrderDetail.objects.create(**new_item_with_unit_g)
                        item_with_unit_g.save()
                    product_recipe_obj = ProductRecipe.objects.filter(product=product_obj,
                                                                      unit__name='B').first().product_input
                    client_product_obj = ClientProduct.objects.get(product=product_recipe_obj, client=client_obj)
                    client_product_obj.quantity = client_product_obj.quantity - decimal.Decimal(quantity)
                    client_product_obj.save()

                else:
                    if unit_obj.name == 'G':
                        _search_item_with_unit_g_set = OrderDetail.objects.filter(
                            unit__name='G', order=order_sale_obj, product=product_obj)

                        if _search_item_with_unit_g_set.count() > 0:
                            _item_with_unit_g = _search_item_with_unit_g_set.last()
                            _item_with_unit_g.quantity_sold = _item_with_unit_g.quantity_sold + quantity
                            _item_with_unit_g.save()
                        else:
                            new_detail_order = {
                                'order': order_sale_obj,
                                'product': product_obj,
                                'quantity_sold': quantity,
                                'price_unit': price,
                                'unit': unit_obj,
                                'status': 'V'
                            }
                            new_detail_order_obj = OrderDetail.objects.create(**new_detail_order)
                            new_detail_order_obj.save()
                    elif unit_obj.name == 'B':
                        _search_item_with_unit_b_set = OrderDetail.objects.filter(
                            unit__name='B', order=order_sale_obj, product=product_obj)

                        if _search_item_with_unit_b_set.count() > 0:
                            _item_with_unit_b = _search_item_with_unit_b_set.last()
                            _item_with_unit_b.quantity_sold = _item_with_unit_b.quantity_sold + quantity
                            _item_with_unit_b.save()
                        else:
                            new_detail_order = {
                                'order': order_sale_obj,
                                'product': product_obj,
                                'quantity_sold': quantity,
                                'price_unit': price,
                                'unit': unit_obj,
                                'status': 'V'
                            }
                            new_detail_order_obj = OrderDetail.objects.create(**new_detail_order)
                            new_detail_order_obj.save()

            store_product_id = int(detail['Store'])

            if _type == 'V':
                if unit_obj.name == 'G':

                    # output sales
                    kardex_ouput(store_product_id, quantity, order_detail_obj=new_detail_order_obj)
                    # get iron supply
                    product_supply_obj = get_iron_man(product_id)
                    subsidiary_store_supply_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj,
                                                                              category='I')

                    try:
                        product_store_supply_obj = ProductStore.objects.get(product=product_supply_obj,
                                                                            subsidiary_store=subsidiary_store_supply_obj)
                    except ProductStore.DoesNotExist:
                        product_store_supply_obj = None

                    if product_store_supply_obj is None:
                        product_store_supply_obj = ProductStore(
                            product=product_supply_obj,
                            subsidiary_store=subsidiary_store_supply_obj,
                            stock=quantity
                        )
                        product_store_supply_obj.save()
                        kardex_initial(product_store_supply_obj, quantity,
                                       product_supply_obj.calculate_minimum_price_sale(),
                                       order_detail_obj=new_detail_order_obj)
                    else:
                        # input supplies
                        kardex_input(product_store_supply_obj.id, quantity,
                                     product_supply_obj.calculate_minimum_price_sale(),
                                     order_detail_obj=new_detail_order_obj)
                elif unit_obj.name == 'BG':
                    # output sales
                    kardex_ouput(store_product_id, quantity, order_detail_obj=item_with_unit_b)
                elif unit_obj.name == 'GBC':
                    # output sales
                    kardex_ouput(store_product_id, quantity, order_detail_obj=item_with_unit_g)
                else:
                    kardex_ouput(store_product_id, quantity, order_detail_obj=new_detail_order_obj)

        if _type == 'E':
            if _bill_type == 'F':

                r = send_bill_nubefact(order_sale_obj.id, is_demo)
                msg_sunat = r.get('sunat_description')
                sunat_pdf = r.get('enlace_del_pdf')
                codigo_hash = r.get('codigo_hash')
                if codigo_hash:
                    order_bill_obj = OrderBill(order=order_sale_obj,
                                               serial=r.get('serie'),
                                               type=r.get('tipo_de_comprobante'),
                                               sunat_status=r.get('aceptada_por_sunat'),
                                               sunat_description=r.get('sunat_description'),
                                               user=user_obj,
                                               sunat_enlace_pdf=r.get('enlace_del_pdf'),
                                               code_qr=r.get('cadena_para_codigo_qr'),
                                               code_hash=r.get('codigo_hash'),
                                               n_receipt=r.get('numero'),
                                               status='E',
                                               created_at=order_sale_obj.create_at,
                                               is_demo=value_is_demo
                                               )
                    order_bill_obj.save()
                else:
                    objects_to_delete = OrderDetail.objects.filter(order=order_sale_obj)
                    objects_to_delete.delete()
                    order_sale_obj.delete()
                    if r.get('errors'):
                        data = {'error': str(r.get('errors'))}
                    elif r.get('error'):
                        data = {'error': str(r.get('error'))}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

            elif _bill_type == 'B':
                r = send_receipt_nubefact(order_sale_obj.id, is_demo)
                msg_sunat = r.get('sunat_description')
                sunat_pdf = r.get('enlace_del_pdf')
                codigo_hash = r.get('codigo_hash')
                if codigo_hash:
                    order_bill_obj = OrderBill(order=order_sale_obj,
                                               serial=r.get('serie'),
                                               type=r.get('tipo_de_comprobante'),
                                               sunat_status=r.get('aceptada_por_sunat'),
                                               sunat_description=r.get('sunat_description'),
                                               user=user_obj,
                                               sunat_enlace_pdf=r.get('enlace_del_pdf'),
                                               code_qr=r.get('cadena_para_codigo_qr'),
                                               code_hash=r.get('codigo_hash'),
                                               n_receipt=r.get('numero'),
                                               status='E',
                                               created_at=order_sale_obj.create_at,
                                               is_demo=value_is_demo
                                               )
                    order_bill_obj.save()
                else:
                    objects_to_delete = OrderDetail.objects.filter(order=order_sale_obj)
                    objects_to_delete.delete()
                    order_sale_obj.delete()
                    if r.get('errors'):
                        data = {'error': str(r.get('errors'))}
                    elif r.get('error'):
                        data = {'error': str(r.get('error'))}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

        # subsidiary_obj = get_subsidiary_by_user(user_obj)
        # sales_store = SubsidiaryStore.objects.filter(
        #     subsidiary=subsidiary_obj, category='V').first()

        # products = Product.objects.all().order_by('id')
        # products = Product.objects.filter(productstore__subsidiary_store=sales_store).order_by('id')

        # tpl = loader.get_template('sales/sales_grid_tab2.html')
        # context = ({'products': products, 'sales_store': sales_store, 'is_render': True, })

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'msg_sunat': msg_sunat,
            'sunat_pdf': sunat_pdf,
            # 'grid': tpl.render(context),
        }, status=HTTPStatus.OK)

    return JsonResponse({
        'message': 'La Venta se Realizo correctamente.',
    }, status=HTTPStatus.OK)


@csrf_exempt
def generate_receipt_random(request):
    global data
    if request.method == 'POST':
        product = request.POST.get('create_product')
        truck = request.POST.get('id_truck')
        client = request.POST.get('id_client_name')
        date = request.POST.get('date')
        is_demo = False
        value_is_demo = 'P'
        if request.POST.get('demo') == '0':
            is_demo = True
            value_is_demo = 'D'

        price = decimal.Decimal(request.POST.get('price'))
        truck_obj = Truck.objects.get(id=int(truck))
        client_obj = Client.objects.get(pk=int(client))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        product_obj = Product.objects.get(id=int(product))
        unit = product_obj.calculate_minimum_unit_id()
        unit_obj = Unit.objects.get(id=unit)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_sales_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='V')

        counter = int(request.POST.get('counter')) + 1
        quantity_min = 1
        limit = 100
        quantity_max = math.floor(limit / price)
        send_dict = []

        for x in range(1, counter, 1):

            # item_dict = {
            #     'quantity': random.randint(quantity_min, quantity_max),
            #     'total': decimal.Decimal(quantity * price)
            # }

            quantity = random.randint(quantity_min, quantity_max)
            total = decimal.Decimal(quantity * price)

            order_obj = Order(type='E',
                              client=client_obj,
                              user=user_obj,
                              total=total,
                              subsidiary_store=subsidiary_store_sales_obj,
                              truck=truck_obj,
                              create_at=date)
            order_obj.save()
            detail_order_obj = OrderDetail(order=order_obj,
                                           product=product_obj,
                                           quantity_sold=quantity,
                                           price_unit=price,
                                           unit=unit_obj,
                                           status='V')
            detail_order_obj.save()
            
            r = send_receipt_nubefact(order_obj.id, is_demo)
            codigo_hash = r.get('codigo_hash')
            if codigo_hash:
                order_bill_obj = OrderBill(order=order_obj,
                                           serial=r.get('serie'),
                                           type=r.get('tipo_de_comprobante'),
                                           sunat_status=r.get('aceptada_por_sunat'),
                                           sunat_description=r.get('sunat_description'),
                                           user=user_obj,
                                           sunat_enlace_pdf=r.get('enlace_del_pdf'),
                                           code_qr=r.get('cadena_para_codigo_qr'),
                                           code_hash=r.get('codigo_hash'),
                                           n_receipt=r.get('numero'),
                                           status='E',
                                           created_at=order_obj.create_at,
                                           is_demo=value_is_demo
                                           )
                order_bill_obj.save()
            else:
                objects_to_delete = OrderDetail.objects.filter(order=order_obj)
                objects_to_delete.delete()
                order_obj.delete()
                if r.get('errors'):
                    data = {'error': str(r.get('errors'))}
                elif r.get('error'):
                    data = {'error': str(r.get('error'))}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        return JsonResponse({
            'msg_sunat': 'Boletas enviadas correctamente',
        }, status=HTTPStatus.OK)


def calculate_minimum_unit(quantity, unit_obj, product_obj):
    product_detail = ProductDetail.objects.filter(
        product=product_obj).annotate(Min('quantity_minimum')).first()
    product_detail_sent = ProductDetail.objects.get(product=product_obj, unit=unit_obj)
    if product_detail.quantity_minimum > 1:
        new_quantity = quantity * product_detail.quantity_minimum
    else:
        new_quantity = quantity * product_detail.quantity_minimum * product_detail_sent.quantity_minimum
    return new_quantity


def kardex_initial(
        product_store_obj,
        stock,
        price_unit,
        purchase_detail_obj=None,
        requirement_detail_obj=None,
        programming_invoice_obj=None,
        manufacture_detail_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        order_detail_obj=None,
        loan_payment_obj=None,
        ball_change_obj=None,
        advance_detail_obj=None,
):
    new_kardex = {
        'operation': 'C',
        'quantity': 0,
        'price_unit': 0,
        'price_total': 0,
        'remaining_quantity': decimal.Decimal(stock),
        'remaining_price': decimal.Decimal(price_unit),
        'remaining_price_total': decimal.Decimal(stock) * decimal.Decimal(price_unit),
        'product_store': product_store_obj,
        'purchase_detail': purchase_detail_obj,
        'requirement_detail': requirement_detail_obj,
        'programming_invoice': programming_invoice_obj,
        'manufacture_detail': manufacture_detail_obj,
        'guide_detail': guide_detail_obj,
        'distribution_detail': distribution_detail_obj,
        'order_detail': order_detail_obj,
        'loan_payment': loan_payment_obj,
        'ball_change': ball_change_obj,
        'advance_detail': advance_detail_obj
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()


def kardex_input(
        product_store_id,
        quantity_purchased,
        price_unit,
        purchase_detail_obj=None,
        requirement_detail_obj=None,
        programming_invoice_obj=None,
        manufacture_detail_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        order_detail_obj=None,
        loan_payment_obj=None,
        ball_change_obj=None,
        advance_detail_obj=None,
):
    product_store = ProductStore.objects.get(pk=int(product_store_id))

    old_stock = product_store.stock
    new_quantity = decimal.Decimal(quantity_purchased)
    new_stock = old_stock + new_quantity  # Cantidad nueva de stock
    new_price_unit = decimal.Decimal(price_unit)
    new_price_total = new_quantity * new_price_unit

    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).last()
    last_remaining_quantity = last_kardex.remaining_quantity
    last_remaining_price_total = last_kardex.remaining_price_total

    new_remaining_quantity = last_remaining_quantity + new_quantity
    new_remaining_price = (decimal.Decimal(last_remaining_price_total) +
                           new_price_total) / new_remaining_quantity
    new_remaining_price_total = new_remaining_quantity * new_remaining_price

    new_kardex = {
        'operation': 'E',
        'quantity': new_quantity,
        'price_unit': new_price_unit,
        'price_total': new_price_total,
        'remaining_quantity': new_remaining_quantity,
        'remaining_price': new_remaining_price,
        'remaining_price_total': new_remaining_price_total,
        'product_store': product_store,
        'purchase_detail': purchase_detail_obj,
        'requirement_detail': requirement_detail_obj,
        'programming_invoice': programming_invoice_obj,
        'manufacture_detail': manufacture_detail_obj,
        'guide_detail': guide_detail_obj,
        'distribution_detail': distribution_detail_obj,
        'order_detail': order_detail_obj,
        'loan_payment': loan_payment_obj,
        'ball_change': ball_change_obj,
        'advance_detail': advance_detail_obj,
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()

    product_store.stock = new_stock
    product_store.save()


def kardex_ouput(
        product_store_id,
        quantity_sold,
        order_detail_obj=None,
        programming_invoice_obj=None,
        manufacture_recipe_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        loan_payment_obj=None,
        ball_change_obj=None,
):
    product_store = ProductStore.objects.get(pk=int(product_store_id))

    old_stock = product_store.stock
    new_stock = old_stock - decimal.Decimal(quantity_sold)
    new_quantity = decimal.Decimal(quantity_sold)

    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).last()
    last_remaining_quantity = last_kardex.remaining_quantity
    old_price_unit = last_kardex.remaining_price

    new_price_total = old_price_unit * new_quantity

    new_remaining_quantity = last_remaining_quantity - new_quantity
    new_remaining_price = old_price_unit
    new_remaining_price_total = new_remaining_quantity * new_remaining_price
    new_kardex = {
        'operation': 'S',
        'quantity': new_quantity,
        'price_unit': old_price_unit,
        'price_total': new_price_total,
        'remaining_quantity': new_remaining_quantity,
        'remaining_price': new_remaining_price,
        'remaining_price_total': new_remaining_price_total,
        'product_store': product_store,
        'programming_invoice': programming_invoice_obj,
        'manufacture_recipe': manufacture_recipe_obj,
        'order_detail': order_detail_obj,
        'guide_detail': guide_detail_obj,
        'distribution_detail': distribution_detail_obj,
        'loan_payment': loan_payment_obj,
        'ball_change': ball_change_obj,
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()

    product_store.stock = new_stock
    product_store.save()


def generate_invoice(request):
    if request.method == 'GET':
        id_order = request.GET.get('order', '')

        # print(numero_a_letras(145))

        r = send_bill_nubefact(id_order)

        return JsonResponse({
            'success': True,
            'msg': r.get('errors'),
            # 'numero_a_letras': numero_a_letras(decimal.Decimal(id_order)),
            'numero_a_moneda': numero_a_moneda(decimal.Decimal(id_order)),

            'parameters': r.get('params'),
        }, status=HTTPStatus.OK)


def get_sales_by_subsidiary_store(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/order_sales_list.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        orders = None
        if subsidiary_obj is not None:
            subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
            orders = Order.objects.filter(subsidiary_store=subsidiary_store_obj)
            start_date = str(request.POST.get('start-date'))
            end_date = str(request.POST.get('end-date'))
            by_units = str(request.POST.get('by-units', 'NO-UNIT'))

            if start_date == end_date:
                orders = orders.filter(create_at__date=start_date, type__in=['V', 'R'])
            else:
                orders = orders.filter(create_at__date__range=[start_date, end_date], type__in=['V', 'R'])
            if orders:
                if by_units == 'NO-UNIT':
                    return JsonResponse({
                        'grid': get_dict_order_queries(orders, is_pdf=False, is_unit=False),
                    }, status=HTTPStatus.OK)
                elif by_units == 'UNIT':
                    return JsonResponse({
                        'grid': get_dict_order_by_units(orders, is_pdf=False, is_unit=True),
                    }, status=HTTPStatus.OK)
            else:
                data = {'error': "No hay operaciones registradas"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
        else:
            data = {'error': "No hay sucursal"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response


def get_dict_order_queries(order_set, is_pdf=False, is_unit=False):
    dictionary = []
    sum = 0

    for o in order_set:

        _order_detail = o.orderdetail_set.all()

        order = {
            'id': o.id,
            'status': o.get_status_display(),
            'client': o.client,
            'user': o.user,
            'total': o.total,
            'subsidiary': o.subsidiary_store.subsidiary.name,
            'create_at': o.create_at,
            'order_detail_set': [],
            'type': o.get_type_display(),
            'details': _order_detail.count()
        }
        sum = sum + o.total

        for d in _order_detail:
            order_detail = {
                'id': d.id,
                'product': d.product.name,
                'unit': d.unit.name,
                'quantity_sold': d.quantity_sold,
                'price_unit': d.price_unit,
                'multiply': d.multiply,
            }
            order.get('order_detail_set').append(order_detail)

        dictionary.append(order)

    tpl = loader.get_template('sales/order_sales_grid_list.html')
    context = ({
        'dictionary': dictionary,
        'sum': sum,
        'is_unit': is_unit,
        'is_pdf': is_pdf,
    })
    return tpl.render(context)


def get_dict_order_by_units(order_set, is_pdf=False, is_unit=True):
    dictionary = []
    sum_10kg = 0
    sum_5kg = 0
    sum_45kg = 0
    sum_15kg = 0
    sum = 0

    for o in order_set:
        order_detail = {}
        subtotal = 0
        _order_detail = o.orderdetail_set.all()
        ball_5kg = get_quantity_ball_5kg(_order_detail)
        ball_10kg = get_quantity_ball_10kg(_order_detail)
        ball_45kg = get_quantity_ball_45kg(_order_detail)
        ball_15kg = get_quantity_ball_15kg(_order_detail)

        s10 = ball_10kg.get('g') + ball_10kg.get('gbc') + ball_10kg.get('bg')
        s5 = ball_5kg.get('g') + ball_5kg.get('gbc') + ball_5kg.get('bg')
        s45 = ball_45kg.get('g') + ball_45kg.get('gbc') + ball_45kg.get('bg')
        s15 = ball_15kg.get('g') + ball_15kg.get('gbc') + ball_15kg.get('bg')

        sum_10kg = sum_10kg + s10
        sum_5kg = sum_5kg + s5
        sum_45kg = sum_45kg + s45
        sum_15kg = sum_15kg + s15

        product_dict = [
            {'pk': 1, 'name': 'BALON DE 10 KG', 'b': ball_10kg.get('b'), 'g': ball_10kg.get('g'),
             'gbc': ball_10kg.get('gbc'), 'bg': ball_10kg.get('bg'), 'sum': s10},
            {'pk': 2, 'name': 'BALON DE 5KG', 'b': ball_5kg.get('b'), 'g': ball_5kg.get('g'),
             'gbc': ball_5kg.get('gbc'), 'bg': ball_5kg.get('bg'), 'sum': s5},
            {'pk': 3, 'name': 'BALON DE 45 KG', 'b': ball_45kg.get('b'), 'g': ball_45kg.get('g'),
             'gbc': ball_45kg.get('gbc'), 'bg': ball_45kg.get('bg'), 'sum': s45},
            {'pk': 12, 'name': 'BALON DE 15 KG', 'b': ball_15kg.get('b'), 'g': ball_15kg.get('g'),
             'gbc': ball_15kg.get('gbc'), 'bg': ball_15kg.get('bg'), 'sum': s15},
        ]

        for d in _order_detail:
            order_detail = {
                'id': d.id,
                'product': d.product.name,
                'unit': d.unit.name,
                'quantity_sold': d.quantity_sold,
                'price_unit': d.price_unit,
                'multiply': d.multiply,
            }
            subtotal += d.quantity_sold * d.price_unit

        order = {
            'id': o.id,
            'status': o.get_status_display(),
            'client': o.client,
            'user': o.user,
            'total': o.total,
            'subsidiary': o.subsidiary_store.subsidiary.name,
            'create_at': o.create_at,
            'order_detail_set': [],
            'product_dict': product_dict,
            'type': o.get_type_display(),
            'details': _order_detail.count()
        }
        order.get('order_detail_set').append(order_detail)

        sum = sum + subtotal

        dictionary.append(order)

    tpl = loader.get_template('sales/order_sales_grid_list.html')
    context = ({
        'dictionary': dictionary,
        'sum': sum,
        'sum_10kg': sum_10kg,
        'sum_5kg': sum_5kg,
        'sum_45kg': sum_45kg,
        'sum_15kg': sum_15kg,
        'is_unit': is_unit,
        'is_pdf': is_pdf,
    })
    return tpl.render(context)


def get_quantity_ball_xkg(order_detail_set=None, product_id=0):
    _b = order_detail_set.filter(unit__name='B', product__id=product_id).values_list('quantity_sold', flat=True)
    _g = order_detail_set.filter(unit__name='G', product__id=product_id).values_list('quantity_sold', flat=True)
    _gbc = order_detail_set.filter(unit__name='GBC', product__id=product_id).values_list('quantity_sold', flat=True)
    _bg = order_detail_set.filter(unit__name='BG', product__id=product_id).values_list('quantity_sold', flat=True)
    if _b.exists():
        _b = _b.first()
    else:
        _b = 0
    if _g.exists():
        _g = _g.first()
    else:
        _g = 0
    if _gbc.exists():
        _gbc = _gbc.first()
    else:
        _gbc = 0
    if _bg.exists():
        _bg = _bg.first()
    else:
        _bg = 0

    context = ({
        'b': _b,
        'g': _g,
        'gbc': _gbc,
        'bg': _bg,
    })
    return context


def get_quantity_ball_5kg(order_detail_set):
    return get_quantity_ball_xkg(order_detail_set=order_detail_set, product_id=2)


def get_quantity_ball_10kg(order_detail_set):
    return get_quantity_ball_xkg(order_detail_set=order_detail_set, product_id=1)


def get_quantity_ball_45kg(order_detail_set):
    return get_quantity_ball_xkg(order_detail_set=order_detail_set, product_id=3)


def get_quantity_ball_15kg(order_detail_set):
    return get_quantity_ball_xkg(order_detail_set=order_detail_set, product_id=12)


def get_sales_all_subsidiaries(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/all_order_sales_list.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        subsidiary_store_set = SubsidiaryStore.objects.filter(category='V')
        orders = Order.objects.filter(subsidiary_store__in=subsidiary_store_set)
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        by_units = str(request.POST.get('by-units', 'NO-UNIT'))

        if start_date == end_date:
            orders = orders.filter(create_at__date=start_date, type__in=['V', 'R'])
        else:
            orders = orders.filter(create_at__date__range=[start_date, end_date], type__in=['V', 'R'])
        if orders:
            if by_units == 'NO-UNIT':
                return JsonResponse({
                    'grid': get_dict_order_queries(orders, is_pdf=False, is_unit=False),
                }, status=HTTPStatus.OK)
            elif by_units == 'UNIT':
                return JsonResponse({
                    'grid': get_dict_order_by_units(orders, is_pdf=False, is_unit=True),
                }, status=HTTPStatus.OK)
        else:
            data = {'error': "No hay operaciones registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_general_orders_by_unit(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/order_by_unit_list.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        subsidiary_store_set = SubsidiaryStore.objects.filter(category='V')
        orders = Order.objects.filter(subsidiary_store__in=subsidiary_store_set)
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        by_units = str(request.POST.get('by-units', 'NO-UNIT'))

        if start_date == end_date:
            orders = orders.filter(create_at__date=start_date, type__in=['V', 'R'])
        else:
            orders = orders.filter(create_at__date__range=[start_date, end_date], type__in=['V', 'R'])
        if orders:
            return JsonResponse({
                'grid': get_dict_orders_by_units(orders, is_pdf=False, is_unit=True),
            }, status=HTTPStatus.OK)
        else:
            data = {'error': "No hay operaciones registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_dict_orders_by_units(order_set, is_pdf=False, is_unit=True):
    dictionary = []
    summation = 0
    summation_10kg = 0
    summation_5kg = 0
    summation_45kg = 0
    summation_15kg = 0
    for s in Subsidiary.objects.all().values('id', 'name'):
        subsidiary = {
            'id': s['id'],
            'name': s['name'],
            'total': 0,
            'total_10kg': 0,
            'total_5kg': 0,
            'total_45kg': 0,
            'total_15kg': 0,
        }
        total_10kg = 0
        total_5kg = 0
        total_45kg = 0
        total_15kg = 0
        total = 0
        subtotal = 0
        for o in order_set.filter(subsidiary_store__subsidiary_id=s['id']).order_by(o.create_at):
            _order_detail = o.orderdetail_set.all()
            ball_5kg = get_quantity_ball_5kg(_order_detail)
            ball_10kg = get_quantity_ball_10kg(_order_detail)
            ball_45kg = get_quantity_ball_45kg(_order_detail)
            ball_15kg = get_quantity_ball_15kg(_order_detail)

            s10 = ball_10kg.get('g') + ball_10kg.get('gbc') + ball_10kg.get('bg')
            s5 = ball_5kg.get('g') + ball_5kg.get('gbc') + ball_5kg.get('bg')
            s45 = ball_45kg.get('g') + ball_45kg.get('gbc') + ball_45kg.get('bg')
            s15 = ball_15kg.get('g') + ball_15kg.get('gbc') + ball_15kg.get('bg')

            total_10kg = total_10kg + s10
            total_5kg = total_5kg + s5
            total_45kg = total_45kg + s45
            total_15kg = total_15kg + s15
            total = total + o.total
        #     for od in o.orderdetail_set.all():
        #         subtotal = od.quantity_sold * od.price_unit
        #
        # total = total + subtotal

        subsidiary['total'] = total
        subsidiary['total_10kg'] = total_10kg
        subsidiary['total_5kg'] = total_5kg
        subsidiary['total_45kg'] = total_45kg
        subsidiary['total_15kg'] = total_15kg

        dictionary.append(subsidiary)

        summation_10kg = summation_10kg + total_10kg
        summation_5kg = summation_5kg + total_5kg
        summation_45kg = summation_45kg + total_45kg
        summation_15kg = summation_15kg + total_15kg
        summation = summation + total

    tpl = loader.get_template('sales/order_by_unit_grid_list.html')
    context = ({
        'dictionary': dictionary,
        'sum': summation,
        'sum_10kg': summation_10kg,
        'sum_5kg': summation_5kg,
        'sum_45kg': summation_45kg,
        'sum_15kg': summation_15kg,
        'is_unit': is_unit,
        'is_pdf': is_pdf,
    })
    return tpl.render(context)


def get_products_by_subsidiary(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary = get_subsidiary_by_user(user_obj)
    subsidiary_stores = SubsidiaryStore.objects.filter(subsidiary=subsidiary)
    form_subsidiary_store = FormSubsidiaryStore()

    return render(request, 'sales/product_by_subsidiary.html', {
        'form': form_subsidiary_store,
        'subsidiary_stores': subsidiary_stores
    })


def new_subsidiary_store(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        name = request.POST.get('name')
        category = request.POST.get('category', '')

        try:
            subsidiary_store_obj = SubsidiaryStore(
                subsidiary=subsidiary_obj,
                name=name,
                category=category
            )
            subsidiary_store_obj.save()
        except DatabaseError as e:
            data = {'error': str(e)}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        return JsonResponse({
            'success': True,
            'message': 'Registrado con exito.',
        }, status=HTTPStatus.OK)


def get_recipe(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)

    products = Product.objects.filter(is_manufactured=True)
    products_insume = Product.objects.filter(is_supply=True)

    return render(request, 'sales/product_recipe.html', {
        'products': products,
        'products_insume': products_insume,
    })


def get_manufacture(request):
    products_insume = Product.objects.filter(
        is_manufactured=True, recipes__isnull=False).distinct('name')
    inputs = Product.objects.filter(is_supply=True)
    mydate = datetime.now()
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    my_subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='I')
    formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
    return render(request, 'sales/recipe_list.html', {
        'products_insume': products_insume,
        'my_subsidiary_store': my_subsidiary_store_obj,
        'date': formatdate,
        'context': validate_manufacture_pendient(subsidiary_obj),
        'inputs': inputs
    })


def get_unit_by_product(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        units = Unit.objects.filter(productdetail__product__id=pk)
        serialized_obj = serializers.serialize('json', units)

    return JsonResponse({'units_serial': serialized_obj})


def get_price_by_product(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        product_detail_obj = ProductDetail.objects.filter(product_id=int(pk)).first()
        price = product_detail_obj.price_sale

    return JsonResponse({'price_unit': price})


def create_recipe(request):
    if request.method == 'GET':
        recipe_request = request.GET.get('recipe_dic', '')
        data_recipe = json.loads(recipe_request)

        for detail in data_recipe['Details']:
            product_create_id = str(detail["ProductCreate"])
            product_create_obj = Product.objects.get(id=product_create_id)

            product_insume_id = str(detail["ProductoInsume"])
            product_insume_obj = Product.objects.get(id=product_insume_id)

            quantity = decimal.Decimal(detail["Quantity"])

            unit_id = str(detail["Unit"])
            unit_obj = Unit.objects.get(id=unit_id)

            price = decimal.Decimal(detail["Price"])

            recipe_product = {
                'product': product_create_obj,
                'product_input': product_insume_obj,
                'quantity': quantity,
                'unit': unit_obj,
                'price': price

            }
            new_recipe_obj = ProductRecipe.objects.create(**recipe_product)
            new_recipe_obj.save()

        return JsonResponse({
            'message': 'La operaciòn se Realizo correctamente.',
        }, status=HTTPStatus.OK)


def get_price_and_total_by_product_recipe(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        product_recipe_obj = ProductRecipe.objects.filter(product__id=int(pk)).first()
        quantity = decimal.Decimal(request.GET.get('quantity', ''))
        price_unit = product_recipe_obj.price
        total = quantity * price_unit

    return JsonResponse({'price_unit': price_unit, 'total': total})


def get_stock_insume_by_product_recipe(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        quantity_request = decimal.Decimal(request.GET.get('quantity'))
        status = request.GET.get('status', '')
        product_recipe_set = ProductRecipe.objects.filter(product__id=int(pk))
        product_create_obj = Product.objects.get(id=int(pk))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_supplies_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='I')
        dictionary = []

        for i in product_recipe_set.all():
            current_stock_of_supply = i.product_input.productstore_set.filter(
                subsidiary_store=subsidiary_store_supplies_obj).first().stock
            total_quantity_request = i.quantity * quantity_request
            total_quantity_remaining = current_stock_of_supply - total_quantity_request
            detail = {
                'id': i.product_input.id,
                'name': i.product_input.name,
                'unit': Unit.objects.get(id=i.product_input.calculate_minimum_unit_id()),
                'quantity_supply': i.quantity,
                # 'quantity_supply_galons': float(i.quantity) / float(3785.41),
                'current_stock': current_stock_of_supply,
                'total_quantity_request': total_quantity_request,
                'quantity_remaining_in_stock': total_quantity_remaining,
            }
            dictionary.append(detail)

        tpl = loader.get_template('sales/detail_product_recipe.html')
        context = ({
            'product_details': dictionary,
            'rowspan': len(dictionary) + 1,
            'quantity': quantity_request,
            'status': status,
            'subsidiary_store_insume': subsidiary_store_supplies_obj,
            'product_create': product_create_obj,
        })
        # serialized_data = serializers.serialize('json', product_recipe_set)
        return JsonResponse({
            'success': True,
            # 'form': t.render(c, request),
            'grid': tpl.render(context),
            # 'serialized_data': serialized_data,
            # 'form': t.render(c),
        }, status=HTTPStatus.OK)


def get_context_kardex_glp(subsidiary_obj, pk, is_pdf=False, get_context=False):
    other_subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(pk))  # otro almacen insumos
    my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(
        subsidiary=subsidiary_obj, category='G')  # pluspetrol
    my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj,
                                                                 category='I')  # tu almacen insumos

    product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')
    product_store_obj = ProductStore.objects.get(
        subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)

    kardex_set = Kardex.objects.filter(product_store=product_store_obj)

    tpl = loader.get_template('sales/kardex_glp_grid.html')
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


def get_kardex_glp(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        pk = request.GET.get('subsidiary_store_id', '')
        if pk != '':

            return JsonResponse({
                'success': True,
                'grid': get_context_kardex_glp(subsidiary_obj, pk),
            }, status=HTTPStatus.OK)
        else:
            subsidiary_store_set = SubsidiaryStore.objects.exclude(
                subsidiary=subsidiary_obj).filter(category='I')
            mydate = datetime.now()
            formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
            return render(request, 'sales/kardex_glp.html', {
                'subsidiary_stores': subsidiary_store_set,
                'date': formatdate
            })


def get_only_grid_kardex_glp(request, pk):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    return render(request, 'sales/kardex_glp_grid.html', get_context_kardex_glp(subsidiary_obj, pk, get_context=True))


def create_order_manufacture(request):
    if request.method == 'GET':
        production_request = request.GET.get('production')
        data_production = json.loads(production_request)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        manufacture_obj_val = ManufactureAction.objects.filter(
            status="1", manufacture__subsidiary=subsidiary_obj)

        # ---Cabecera de Manufacturee---
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        code = str(data_production["Code"])
        total = decimal.Decimal((data_production["Total"]).replace(',', '.'))

        new_manufacture_obj = Manufacture(subsidiary=subsidiary_obj, code=code, total=total)
        new_manufacture_obj.save()

        # --Save ManufactureAction--
        new_manufacture_action_obj = ManufactureAction(
            user=user_obj, manufacture=new_manufacture_obj, status="1")
        new_manufacture_action_obj.save()

        # --Save Manufacturedetail--
        for details in data_production['Details']:

            product_create_id = str(details["Product"])
            product_create_obj = Product.objects.get(id=product_create_id)

            quantity_request = decimal.Decimal(details["Quantity"])
            price = decimal.Decimal(details["Price"])

            new_manufacture_detail_obj = ManufactureDetail(manufacture=new_manufacture_obj,
                                                           product_manufacture=product_create_obj,
                                                           quantity=quantity_request, price=price)
            new_manufacture_detail_obj.save()

            for insume in ProductRecipe.objects.filter(product=product_create_obj):
                new_manufacture_recipe_obj = ManufactureRecipe(manufacture_detail=new_manufacture_detail_obj,
                                                               product_input=insume.product_input,
                                                               quantity=insume.quantity * quantity_request)
                new_manufacture_recipe_obj.save()

        return JsonResponse({
            'message': 'La operaciòn se Realizo correctamente.',
        }, status=HTTPStatus.OK)

    else:
        return JsonResponse({
            'error': 'No se puede guardar, existe una Orden pendiente'
        }, status=HTTPStatus.OK)


def orders_manufacture(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        manufactures = Manufacture.objects.filter(subsidiary=subsidiary_obj)
        status = ManufactureAction._meta.get_field('status').choices

        return render(request, 'sales/manufacture_list.html', {
            'manufactures': manufactures,
            'status': status
        })


# Aqui tambien se guardan los productos creados
def update_manufacture_by_id(request):
    if request.method == 'GET':
        manufacture_id = request.GET.get('pk', '')
        status_id = request.GET.get('status', '')
        manufacture_obj = Manufacture.objects.get(id=int(manufacture_id))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        if status_id == '2':  # aprobado
            subsidiary_store_set_obj = SubsidiaryStore.objects.get(
                subsidiary=subsidiary_obj, category='I')
            manufacture_details_set = ManufactureDetail.objects.filter(
                manufacture_id=int(manufacture_id))
            if validate_stock_insume(subsidiary_store_set_obj, manufacture_id):
                for d in manufacture_details_set.all():
                    inputs_set = ManufactureRecipe.objects.filter(manufacture_detail=d)
                    for i in inputs_set:
                        product_store_inputs_obj = ProductStore.objects.get(subsidiary_store=subsidiary_store_set_obj,
                                                                            product=i.product_input)
                        kardex_ouput(product_store_inputs_obj.id,
                                     i.quantity,
                                     manufacture_recipe_obj=i)  # i.quantity = LA CANTIDAD QUE SE DESCONTARA DEL STOCK DEL INSUMO

                new_manufacture_action_obj = ManufactureAction(user=user_obj, date=datetime.now(),
                                                               manufacture=manufacture_obj, status=status_id)
                new_manufacture_action_obj.save()
            else:
                data = {'error': 'No se pudo Aprobar la solicitud por falta de stock de un insumo'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        elif status_id == '3':  # produccion
            new_manufacture_action_obj = ManufactureAction(user=user_obj, date=datetime.now(),
                                                           manufacture=manufacture_obj, status=status_id)
            new_manufacture_action_obj.save()

        elif status_id == '4':
            subsidiary_store_set_obj = SubsidiaryStore.objects.get(
                subsidiary=subsidiary_obj, category='V')
            manufacture_details_set = ManufactureDetail.objects.filter(
                manufacture_id=int(manufacture_id))
            for d in manufacture_details_set.all():
                price_unit = d.price / d.quantity
                try:
                    product_store_create = ProductStore.objects.get(subsidiary_store=subsidiary_store_set_obj,
                                                                    product=d.product_manufacture)
                except ProductStore.DoesNotExist:
                    product_store_create = None

                if product_store_create is None:
                    product_store_create = ProductStore(product=d.product_manufacture, stock=d.quantity,
                                                        subsidiary_store=subsidiary_store_set_obj)
                    product_store_create.save()
                    kardex_initial(product_store_create, d.quantity,
                                   price_unit, manufacture_detail_obj=d)
                else:
                    kardex_input(product_store_create.id, d.quantity,
                                 price_unit, manufacture_detail_obj=d)

            new_manufacture_action_obj = ManufactureAction(user=user_obj, date=datetime.now(),
                                                           manufacture=manufacture_obj, status=status_id)
            new_manufacture_action_obj.save()

        elif status_id == '5':
            new_manufacture_action_obj = ManufactureAction(user=user_obj, date=datetime.now(),
                                                           manufacture=manufacture_obj, status=status_id)
            new_manufacture_action_obj.save()

        return JsonResponse({
            'message': 'Se cambio el estado correctamente.',
        }, status=HTTPStatus.OK)


def validate_stock_insume(subsidiary_store, manufacture_id):
    manufacture_details_set = ManufactureDetail.objects.filter(manufacture_id=int(manufacture_id))
    for d in manufacture_details_set.all():
        inputs_set = ManufactureRecipe.objects.filter(manufacture_detail=d)
        for i in inputs_set:
            product_store_inputs_obj = ProductStore.objects.get(subsidiary_store=subsidiary_store,
                                                                product=i.product_input)
            if product_store_inputs_obj.stock < i.quantity:
                return False
    return True


def validate_manufacture_pendient(subsidiary_obj):
    for m in Manufacture.objects.filter(subsidiary=subsidiary_obj):
        last_action = ManufactureAction.objects.filter(manufacture=m).last()
        if last_action.status == '1':
            context = ({
                'code': last_action.manufacture.code,
                'flag': False,
            })
            return context
    return {'flag': True}


def order_list(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        # clients = Client.objects.filter(clientassociate__subsidiary=subsidiary_obj)
        client_set = Client.objects.filter(
            order__isnull=False, order__subsidiary=subsidiary_obj, order__type__in=['V', 'R']
        ).distinct('id').values('id', 'names')

        return render(request, 'sales/account_status_list.html', {
            'client_set': client_set,
            'formatdate': formatdate,
        })


def get_dict_orders(client_obj=None, is_pdf=False, start_date=None, end_date=None):
    sum_quantity_total = 0
    order_set = Order.objects.filter(
        client=client_obj, create_at__date__range=[start_date, end_date], type__in=['V', 'R']
    ).prefetch_related(
        Prefetch(
            'orderdetail_set', queryset=OrderDetail.objects.select_related('product', 'unit').prefetch_related(
                Prefetch(
                    'loanpayment_set',
                    queryset=LoanPayment.objects.select_related('order_detail__order').prefetch_related(
                        Prefetch(
                            'transactionpayment_set',
                            queryset=TransactionPayment.objects.select_related('loan_payment__order_detail__order')
                        )
                    )
                ),
                Prefetch('ballchange_set'),
            )
        ),
        Prefetch(
            'cashflow_set', queryset=CashFlow.objects.select_related('cash')
        ),
    ).select_related('distribution_mobil__truck', 'distribution_mobil__pilot', 'client').order_by('id')

    dictionary = []

    for o in order_set:
        if o.orderdetail_set.all().exists():
            order_detail_set = o.orderdetail_set.all()
            cashflow_set = o.cashflow_set.all()
            new = {
                'id': o.id,
                'type': o.get_type_display(),
                'client': o.client.names,
                'date': o.create_at,
                'distribution_mobil': [],
                'order_detail_set': [],
                'status': o.get_status_display(),
                'total': o.total,
                'subtotal': 0,
                'total_repay_loan': '{:,}'.format(
                    total_remaining_repay_loan(order_detail_set=order_detail_set).quantize(decimal.Decimal('0.00'),
                                                                                           rounding=decimal.ROUND_HALF_EVEN)),
                'total_repay_loan_with_vouchers': total_repay_loan_with_vouchers(order_detail_set=order_detail_set),
                'total_return_loan': '{:,}'.format(
                    round(float(total_return_loan(order_detail_set=order_detail_set)), 2)),
                'total_remaining_repay_loan': '{:,}'.format(
                    total_remaining_repay_loan(order_detail_set=order_detail_set).quantize(decimal.Decimal('0.00'),
                                                                                           rounding=decimal.ROUND_HALF_EVEN)),
                'total_remaining_repay_loan_ball': '{:,}'.format(
                    round(float(total_remaining_repay_loan_ball(order_detail_set=order_detail_set)), 2)),
                'total_remaining_return_loan': '{:,}'.format(
                    round(float(total_remaining_return_loan(order_detail_set=order_detail_set)), 2)),
                'total_ball_changes': total_ball_changes(order_detail_set=order_detail_set),
                'total_spending': '{:,}'.format(round(float(total_cash_flow_spending(cashflow_set=cashflow_set))), 2),
                'details_count': order_detail_set.count(),
                'rowspan': 0,
                'is_review': o.is_review,
                'has_loans': False
            }
            license_plate = '-'
            pilot = '-'
            if o.distribution_mobil:
                license_plate = o.distribution_mobil.truck.license_plate
                pilot = o.distribution_mobil.pilot.full_name
            distribution_mobil = {
                'license_plate': license_plate,
                'pilot': pilot,
            }
            new.get('distribution_mobil').append(distribution_mobil)

            subtotal = 0

            for d in order_detail_set:
                _type = '-'
                if d.unit.name == 'G':
                    _type = 'CANJEADO'
                elif d.unit.name == 'B':
                    _type = 'PRESTADO'

                loan_payment_set = []
                for lp in d.loanpayment_set.all():
                    _payment_type = '-'
                    _cash_flow = None
                    _number_of_vouchers = 0
                    transaction_payment_set = lp.transactionpayment_set.all()
                    truck_ = "-"
                    if transaction_payment_set.exists():
                        transaction_payment = None
                        for t in transaction_payment_set:
                            transaction_payment = t
                        _cash_flow = get_cash_flow(order=o, transactionpayment=transaction_payment)
                        _payment_type = transaction_payment.get_type_display()
                        _number_of_vouchers = transaction_payment.number_of_vouchers

                    if lp.distribution_mobil is not None:
                        truck_ = lp.distribution_mobil.truck.license_plate

                    loan_payment = {
                        'id': lp.id,
                        'quantity': lp.quantity,
                        'number_of_vouchers': _number_of_vouchers,
                        'date': lp.create_at,
                        'operation_date': lp.operation_date,
                        'price': '{:,}'.format(
                            lp.price.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)),
                        'type': _payment_type,
                        'cash_flow': _cash_flow,
                        'license_plate': truck_,
                        'is_review_pay': lp.is_check
                    }
                    loan_payment_set.append(loan_payment)

                loans_count = d.loanpayment_set.all().count()

                if loans_count == 0:
                    rowspan = 1
                else:
                    rowspan = loans_count
                    if not new['has_loans']:
                        new['has_loans'] = True

                order_detail = {
                    'id': d.id,
                    'product_id': d.product.id,
                    'product': d.product.name,
                    'code': d.product.code,
                    'unit': d.unit.name,
                    'type': _type,
                    'quantity_sold': d.quantity_sold,
                    'price_unit': d.price_unit,
                    'multiply': d.multiply,
                    'return_loan': '{:,}'.format(
                        round(float(return_loan(loan_payment_set=d.loanpayment_set.all())), 2)),
                    'repay_loan': '{:,}'.format(round(float(repay_loan(loan_payment_set=d.loanpayment_set.all())), 2)),
                    'repay_loan_ball': repay_loan_ball(loan_payment_set=d.loanpayment_set.all()),
                    'repay_loan_with_vouchers': repay_loan_with_vouchers(loan_payment_set=d.loanpayment_set.all()),
                    'ball_changes': ball_changes(ballchange_set=d.ballchange_set.all()),
                    'loan_payment_set': loan_payment_set,
                    'loans_count': loans_count,
                    'rowspan': rowspan,
                    'has_spending': False
                }
                subtotal += d.quantity_sold * d.price_unit

                new.get('order_detail_set').append(order_detail)
                new['rowspan'] = new['rowspan'] + rowspan

                if d.unit.name == 'G' and o.distribution_mobil:
                    order_detail['has_spending'] = True
                else:
                    order_detail['has_spending'] = False
            new['subtotal'] = round(float(subtotal), 2)
            dictionary.append(new)

    sum_total = 0
    sum_total_repay_loan = 0
    sum_total_repay_loan_with_vouchers = 0
    sum_total_return_loan = 0
    sum_total_remaining_repay_loan = 0
    sum_total_remaining_return_loan = 0
    sum_total_remaining_repay_loan_ball = 0
    sum_total_ball_changes = 0
    sum_total_cash_flow_spending = 0
    difference_debt = 0

    if order_set.exists():
        sum_quantity_total = 0
        for o in order_set:
            order_detail_set = o.orderdetail_set.all()
            cashflow_set = o.cashflow_set.all()
            sum_total_repay_loan += total_repay_loan(order_detail_set=order_detail_set)
            sum_total_repay_loan_with_vouchers += total_repay_loan_with_vouchers(order_detail_set=order_detail_set)
            sum_total_return_loan += total_return_loan(order_detail_set=order_detail_set)
            sum_total_remaining_repay_loan += total_remaining_repay_loan(order_detail_set=order_detail_set)
            sum_total_remaining_return_loan += total_remaining_return_loan(order_detail_set=order_detail_set)
            sum_total_remaining_repay_loan_ball += total_remaining_repay_loan_ball(order_detail_set=order_detail_set)
            sum_total_ball_changes += total_ball_changes(order_detail_set=order_detail_set)
            sum_total_cash_flow_spending += total_cash_flow_spending(cashflow_set=cashflow_set)
            total_quantity_set = order_detail_set.values('quantity_sold').annotate(
                totals_quantity=Sum('quantity_sold')).aggregate(Sum('totals_quantity'))

            sum_quantity_total += total_quantity_set['totals_quantity__sum']
            difference_debt = sum_total_remaining_repay_loan - sum_total_repay_loan

        total_set = order_set.values('client').annotate(totals=Sum('total'))
        sum_total = total_set[0].get('totals')

        # sum_quantity_total = total_quantity_set[0].get('totals_quantity')

    tpl = loader.get_template('sales/account_order_list.html')
    context = ({
        'dictionary': dictionary,
        'sum_total': '{:,}'.format(round(float(sum_total), 2)),
        'sum_total_repay_loan': '{:,}'.format(round(float(sum_total_repay_loan), 2)),
        'sum_total_repay_loan_with_vouchers': '{:,}'.format(round(float(sum_total_repay_loan_with_vouchers), 2)),
        'sum_total_return_loan': '{:,}'.format(round(float(sum_total_return_loan), 2)),
        'sum_total_remaining_repay_loan': '{:,}'.format(round(float(sum_total_remaining_repay_loan), 2)),
        'sum_total_remaining_repay_loan_ball': '{:,}'.format(round(float(sum_total_remaining_repay_loan_ball), 2)),
        'sum_total_remaining_return_loan': '{:,}'.format(round(float(sum_total_remaining_return_loan), 2)),
        'sum_total_ball_changes': '{:,}'.format(round(float(sum_total_ball_changes), 2)),
        'sum_total_cash_flow_spending': '{:,}'.format(round(float(sum_total_cash_flow_spending), 2)),
        'sum_quantity_total': sum_quantity_total,
        'difference_debt': '{:,}'.format(round(float(difference_debt), 2)),
        'is_pdf': is_pdf,
        'client_obj': client_obj,
    })

    return tpl.render(context)


def get_orders_by_client(request):
    if request.method == 'GET':
        client_id = request.GET.get('client_id', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')

        client_obj = Client.objects.get(pk=int(client_id))
        # order_set = Order.objects.filter(client=client_obj, create_at__date__range=[start_date, end_date], type__in=['V', 'R']).order_by('id')

        return JsonResponse({
            'grid': get_dict_orders(client_obj=client_obj, is_pdf=False, start_date=start_date, end_date=end_date),
        }, status=HTTPStatus.OK)


def get_iron_man(product_id):
    product_obj = Product.objects.get(id=product_id)
    subcategory_obj = ProductSubcategory.objects.get(name='FIERRO', product_category__name='FIERRO')
    product_insume_set = ProductRecipe.objects.filter(product=product_obj,
                                                      product_input__product_subcategory=subcategory_obj)
    product_insume_obj = product_insume_set.first().product_input
    return product_insume_obj


def get_order_detail_for_pay(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        detail_id = request.GET.get('detail_id', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        detail_obj = OrderDetail.objects.get(id=int(detail_id))
        order_obj = Order.objects.get(orderdetail=detail_obj)
        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        tpl = loader.get_template('sales/new_payment_from_lending.html')
        context = ({
            'choices_payments': TransactionPayment._meta.get_field('type').choices,
            'detail': detail_obj,
            'order': order_obj,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'date': formatdate,
            'start_date': start_date,
            'end_date': end_date
        })

        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_expenses(request):
    if request.method == 'GET':
        transactionaccount_obj = TransactionAccount.objects.all()
        user_id = request.user.id
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        tpl = loader.get_template('sales/new_expense.html')
        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='104')
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        context = ({
            'choices_document': TransactionAccount._meta.get_field('document_type_attached').choices,
            'transactionaccount': transactionaccount_obj,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'date': formatdate,
            'start_date': start_date,
            'end_date': end_date
        })

        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_expense(request):
    if request.method == 'POST':
        transaction_date = str(request.POST.get('id_date'))
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        type_document = str(request.POST.get('id_transaction_document_type'))
        serie = str(request.POST.get('id_serie'))
        nro = str(request.POST.get('id_nro'))
        total_pay = str(request.POST.get('pay-loan')).replace(',', '.')
        order = int(request.POST.get('id_order'))
        order_obj = Order.objects.get(id=order)
        subtotal = str(request.POST.get('id_subtotal'))
        igv = str(request.POST.get('igv'))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        serie_obj = None
        nro_obj = None
        if serie:
            serie_obj = serie
        if nro:
            nro_obj = nro
        description_expense = str(request.POST.get('id_description'))
        total = str(request.POST.get('id_amount'))
        _account = str(request.POST.get('id_cash'))
        cashflow_set = CashFlow.objects.filter(cash_id=_account, transaction_date__date=transaction_date, type='A')
        check_closed = CashFlow.objects.filter(type='C', transaction_date__date=transaction_date, cash_id=_account)

        if cashflow_set.count() > 0:
            cash_obj = cashflow_set.first().cash

            if check_closed:
                data = {'error': "La caja seleccionada se encuentra cerrada, favor de seleccionar otra"}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            # if decimal.Decimal(total) > decimal.Decimal(total_pay):
            #     data = {
            #         'error': "El monto excede al total de la deuda"}
            #     response = JsonResponse(data)
            #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            #     return response
        else:
            data = {'error': "No existe una Apertura de Caja"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        cashflow_obj = CashFlow(
            transaction_date=transaction_date,
            document_type_attached=type_document,
            serial=serie_obj,
            n_receipt=nro_obj,
            description=description_expense,
            subtotal=subtotal,
            igv=igv,
            total=total,
            order=order_obj,
            type='S',
            cash=cash_obj,
            user=user_obj
        )
        cashflow_obj.save()

        return JsonResponse({
            'message': 'Registro guardado correctamente.',
            'grid': get_dict_orders(client_obj=order_obj.client, is_pdf=False, start_date=start_date, end_date=end_date)
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def new_loan_payment(request):
    data = dict()
    if request.method == 'POST':
        id_detail = int(request.POST.get('detail'))
        start_date = request.POST.get('start_date', '')
        end_date = request.POST.get('end_date', '')
        detail_obj = OrderDetail.objects.get(id=id_detail)
        option = str(request.POST.get('radio'))  # G or B or P
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        payment = 0
        quantity = 0

        if option == 'G':
            _operation_date = request.POST.get('date_return_loan0', '')
            if not validate(_operation_date):
                data = {'error': "Seleccione fecha."}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
            if len(request.POST.get('loan_payment', '')) > 0:
                val = decimal.Decimal(request.POST.get('loan_payment'))
                if 0 < val <= detail_obj.order.total_remaining_repay_loan():
                    transaction_payment_type = str(request.POST.get('transaction_payment_type'))
                    number_of_vouchers = decimal.Decimal(
                        request.POST.get('number_of_vouchers', '0'))
                    code_operation = str(request.POST.get('code_operation'))

                    payment = val

                    if transaction_payment_type == 'D':
                        cash_flow_description = str(request.POST.get('description_deposit'))
                        cash_flow_transact_date_deposit = str(request.POST.get('id_date_deposit'))
                        cash_id = str(request.POST.get('id_cash_deposit'))
                        cash_obj = Cash.objects.get(id=cash_id)
                        order_obj = detail_obj.order

                        cashflow_obj = CashFlow(
                            transaction_date=cash_flow_transact_date_deposit,
                            document_type_attached='O',
                            description=cash_flow_description,
                            order=order_obj,
                            type='D',
                            operation_code=code_operation,
                            total=payment,
                            cash=cash_obj,
                            user=user_obj
                        )
                        cashflow_obj.save()

                        loan_payment_obj = LoanPayment(
                            price=payment,
                            quantity=quantity,
                            product=detail_obj.product,
                            order_detail=detail_obj,
                            operation_date=_operation_date
                        )
                        loan_payment_obj.save()

                        transaction_payment_obj = TransactionPayment(
                            payment=payment,
                            number_of_vouchers=number_of_vouchers,
                            type=transaction_payment_type,
                            operation_code=code_operation,
                            loan_payment=loan_payment_obj
                        )
                        transaction_payment_obj.save()

                    if transaction_payment_type == 'E':

                        cash_flow_transact_date = str(request.POST.get('id_date'))
                        cash_flow_description = str(request.POST.get('id_description'))
                        cash_id = str(request.POST.get('id_cash_efectivo'))
                        cash_obj = Cash.objects.get(id=cash_id)
                        order_obj = detail_obj.order
                        cashflow_set = CashFlow.objects.filter(cash_id=cash_id,
                                                               transaction_date__date=cash_flow_transact_date, type='A')
                        if cashflow_set.count() > 0:
                            cash_obj = cashflow_set.first().cash
                        else:
                            data = {'error': "No existe una Apertura de Caja, Favor de revisar las Control de Cajas"}
                            response = JsonResponse(data)
                            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                            return response

                        cashflow_obj = CashFlow(
                            transaction_date=cash_flow_transact_date,
                            document_type_attached='O',
                            description=cash_flow_description,
                            order=order_obj,
                            type='E',
                            total=payment,
                            cash=cash_obj,
                            user=user_obj
                        )
                        cashflow_obj.save()

                        loan_payment_obj = LoanPayment(
                            price=payment,
                            quantity=quantity,
                            product=detail_obj.product,
                            order_detail=detail_obj,
                            operation_date=_operation_date
                        )
                        loan_payment_obj.save()

                        transaction_payment_obj = TransactionPayment(
                            payment=payment,
                            number_of_vouchers=number_of_vouchers,
                            type=transaction_payment_type,
                            operation_code=code_operation,
                            loan_payment=loan_payment_obj
                        )
                        transaction_payment_obj.save()

                    if transaction_payment_type == 'F':
                        cash_flow_description = str(request.POST.get('id_description_deposit_fise'))
                        cash_flow_transact_date_deposit = str(request.POST.get('id_date_desposit_fise'))
                        cash_id = str(request.POST.get('id_cash_deposit_fise'))
                        cash_obj = Cash.objects.get(id=cash_id)
                        order_obj = detail_obj.order

                        cashflow_obj = CashFlow(
                            transaction_date=cash_flow_transact_date_deposit,
                            document_type_attached='O',
                            description=cash_flow_description,
                            order=order_obj,
                            type='D',
                            operation_code=code_operation,
                            total=payment,
                            cash=cash_obj,
                            user=user_obj
                        )
                        cashflow_obj.save()

                        loan_payment_obj = LoanPayment(
                            price=payment,
                            quantity=quantity,
                            product=detail_obj.product,
                            order_detail=detail_obj,
                        )
                        loan_payment_obj.save()

                        transaction_payment_obj = TransactionPayment(
                            payment=payment,
                            number_of_vouchers=number_of_vouchers,
                            type=transaction_payment_type,
                            operation_code=code_operation,
                            loan_payment=loan_payment_obj
                        )
                        transaction_payment_obj.save()

        else:
            if option == 'B':
                _operation_date = request.POST.get('date_return_loan', '')
                if not validate(_operation_date):
                    data = {'error': "Seleccione fecha."}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

                if len(request.POST.get('loan_quantity', '')) > 0:
                    val = decimal.Decimal(request.POST.get('loan_quantity'))
                    if 0 < val <= detail_obj.quantity_sold:
                        quantity = val
                        loan_payment_obj = LoanPayment(
                            price=detail_obj.price_unit,
                            quantity=quantity,
                            product=detail_obj.product,
                            order_detail=detail_obj,
                            operation_date=_operation_date
                        )
                        loan_payment_obj.save()
                        if detail_obj.order.type == 'V':
                            if detail_obj.unit.name == 'B':
                                product_supply_obj = get_iron_man(detail_obj.product.id)
                                subsidiary_store_supply_obj = SubsidiaryStore.objects.get(
                                    subsidiary=detail_obj.order.subsidiary_store.subsidiary, category='I')
                                try:
                                    product_store_supply_obj = ProductStore.objects.get(product=product_supply_obj,
                                                                                        subsidiary_store=subsidiary_store_supply_obj)
                                    kardex_input(product_store_supply_obj.id, quantity,
                                                 product_supply_obj.calculate_minimum_price_sale(),
                                                 loan_payment_obj=loan_payment_obj)
                                except ProductStore.DoesNotExist:
                                    product_store_supply_obj = ProductStore(
                                        product=product_supply_obj,
                                        subsidiary_store=subsidiary_store_supply_obj,
                                        stock=quantity
                                    )
                                    product_store_supply_obj.save()
                                    kardex_initial(product_store_supply_obj, quantity,
                                                   product_supply_obj.calculate_minimum_price_sale(),
                                                   loan_payment_obj=loan_payment_obj)

            elif option == 'P':
                _operation_date = request.POST.get('date_return_loan2', '')
                if not validate(_operation_date):
                    data = {'error': "Seleccione fecha."}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
                if len(request.POST.get('loan_quantity2', '')) > 0:
                    val = decimal.Decimal(request.POST.get('loan_quantity2'))

                    if 0 < val <= detail_obj.quantity_sold:
                        quantity = val
                        if len(request.POST.get('loan_payment2', '')) > 0:
                            val2 = decimal.Decimal(request.POST.get('loan_payment2'))
                            if 0 < val2 <= detail_obj.multiply():
                                transaction_payment_type = str(
                                    request.POST.get('transaction_payment_type2'))
                                code_operation = str(request.POST.get('code_operation2'))
                                payment = val2
                                unit_price_with_discount = payment / quantity
                                product_detail_obj = ProductDetail.objects.get(product=detail_obj.product,
                                                                               unit=detail_obj.unit)
                                unit_price = product_detail_obj.price_sale
                                _discount = unit_price - unit_price_with_discount

                                if transaction_payment_type == 'D':
                                    cash_flow_transact_date = str(request.POST.get('id_date_desposit2'))
                                    cash_flow_description = str(request.POST.get('description_deposit2'))
                                    cash_id = str(request.POST.get('id_cash_deposit2'))
                                    cash_obj = Cash.objects.get(id=cash_id)
                                    order_obj = detail_obj.order

                                    cashflow_obj = CashFlow(
                                        transaction_date=cash_flow_transact_date,
                                        document_type_attached='O',
                                        description=cash_flow_description,
                                        order=order_obj,
                                        type='D',
                                        operation_code=code_operation,
                                        total=payment,
                                        cash=cash_obj,
                                        user=user_obj
                                    )
                                    cashflow_obj.save()

                                    loan_payment_obj = LoanPayment(
                                        price=unit_price_with_discount,
                                        quantity=quantity,
                                        discount=0.00,
                                        product=detail_obj.product,
                                        order_detail=detail_obj,
                                        operation_date=_operation_date
                                    )
                                    loan_payment_obj.save()

                                    transaction_payment_obj = TransactionPayment(
                                        payment=payment,
                                        type=transaction_payment_type,
                                        operation_code=code_operation,
                                        loan_payment=loan_payment_obj
                                    )
                                    transaction_payment_obj.save()

                                if transaction_payment_type == 'E':

                                    cash_flow_transact_date = str(request.POST.get('id_date2'))
                                    cash_flow_description = str(request.POST.get('id_description2'))
                                    cash_id = str(request.POST.get('id_cash_efectivo2'))
                                    cash_obj = Cash.objects.get(id=cash_id)
                                    order_obj = detail_obj.order
                                    cashflow_set = CashFlow.objects.filter(cash_id=cash_id,
                                                                           transaction_date__date=cash_flow_transact_date,
                                                                           type='A')
                                    if cashflow_set.count() > 0:
                                        cash_obj = cashflow_set.first().cash
                                    else:
                                        data = {
                                            'error': "No existe una Apertura de Caja, Favor de revisar las Control de Cajas"}
                                        response = JsonResponse(data)
                                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                                        return response

                                    cashflow_obj = CashFlow(
                                        transaction_date=cash_flow_transact_date,
                                        document_type_attached='O',
                                        description=cash_flow_description,
                                        order=order_obj,
                                        type='E',
                                        total=payment,
                                        cash=cash_obj,
                                        user=user_obj
                                    )
                                    cashflow_obj.save()

                                    loan_payment_obj = LoanPayment(
                                        price=unit_price_with_discount,
                                        quantity=quantity,
                                        discount=0.00,
                                        product=detail_obj.product,
                                        order_detail=detail_obj,
                                        operation_date=_operation_date
                                    )
                                    loan_payment_obj.save()

                                    transaction_payment_obj = TransactionPayment(
                                        payment=payment,
                                        type=transaction_payment_type,
                                        operation_code=code_operation,
                                        loan_payment=loan_payment_obj
                                    )
                                    transaction_payment_obj.save()

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': get_dict_orders(client_obj=detail_obj.order.client, is_pdf=False, start_date=start_date,
                                    end_date=end_date),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def open_loan_account(order_detail_obj, payment=0, quantity=0):
    new_quantity = decimal.Decimal(quantity)
    new_price_unit = decimal.Decimal(payment)
    new_price_total = new_quantity * new_price_unit
    new_remaining_quantity = new_quantity
    new_remaining_price = new_price_unit
    new_remaining_price_total = new_remaining_quantity * new_remaining_price

    new_loan_account = LoanAccount(
        operation='L',
        quantity=new_quantity,
        price_unit=new_price_unit,
        price_total=new_price_total,
        remaining_quantity=new_remaining_quantity,
        remaining_price=new_remaining_price,
        remaining_price_total=new_remaining_price_total,
        product=order_detail_obj.product,
        order_detail=order_detail_obj,
    )
    new_loan_account.save()


def return_loan_account(order_detail_obj, payment=0, quantity=0):
    new_quantity = decimal.Decimal(quantity)
    new_price_unit = decimal.Decimal(payment)
    new_price_total = new_quantity * new_price_unit

    loan_account_set = LoanAccount.objects.filter(
        client=order_detail_obj.order.client, product=order_detail_obj.product)

    if loan_account_set.count > 0:
        last_loan_account = loan_account_set.last()
        last_remaining_quantity = last_loan_account.remaining_quantity
        last_remaining_price_total = last_loan_account.remaining_price_total

        new_remaining_quantity = last_remaining_quantity + new_quantity
        new_remaining_price = (decimal.Decimal(last_remaining_price_total) +
                               new_price_total) / new_remaining_quantity
        new_remaining_price_total = new_remaining_quantity * new_remaining_price

        new_loan_account = LoanAccount(
            operation='P',
            quantity=new_quantity,
            price_unit=new_price_unit,
            price_total=new_price_total,
            remaining_quantity=new_remaining_quantity,
            remaining_price=new_remaining_price,
            remaining_price_total=new_remaining_price_total,
            product=order_detail_obj.product,
            order_detail=order_detail_obj,
        )
        new_loan_account.save()


def get_order_detail_for_ball_change(request):
    if request.method == 'GET':
        detail_id = request.GET.get('detail_id', '')
        start_date = request.GET.get('_start_date', '')
        end_date = request.GET.get('_end_date', '')
        detail_obj = OrderDetail.objects.get(id=int(detail_id))
        tpl = loader.get_template('sales/new_ball_change.html')
        context = ({
            'choices_status': BallChange._meta.get_field('status').choices,
            'detail': detail_obj,
            'start_date': start_date,
            'end_date': end_date,
        })

        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_ball_change(request):
    if request.method == 'POST':

        id_detail = int(request.POST.get('detail'))
        detail_obj = OrderDetail.objects.get(id=id_detail)
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        quantity = 0
        ball_change_obj = None

        if len(request.POST.get('quantity', '')) > 0:
            val = decimal.Decimal(request.POST.get('quantity'))
            if 0 < val <= detail_obj.quantity_sold:
                status = str(request.POST.get('status'))
                observation = str(request.POST.get('observation'))
                quantity = val

                ball_change_obj = BallChange(
                    status=status,
                    observation=observation,
                    quantity=quantity,
                    product=detail_obj.product,
                    order_detail=detail_obj,
                )
                ball_change_obj.save()

        if detail_obj.order.type == 'V':

            # OUTPUT SALES
            subsidiary_store_sales_obj = detail_obj.order.subsidiary_store
            product_store_sales_obj = ProductStore.objects.get(product=detail_obj.product,
                                                               subsidiary_store=subsidiary_store_sales_obj)
            kardex_ouput(product_store_sales_obj.id, quantity, ball_change_obj=ball_change_obj)

            # INPUT MAINTENANCE
            try:
                subsidiary_store_maintenance_obj = SubsidiaryStore.objects.get(
                    subsidiary=detail_obj.order.subsidiary_store.subsidiary, category='R')
            except SubsidiaryStore.DoesNotExist:
                data = {'error': 'No se encontro el almacen de mantenimiento.'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            try:
                product_store_maintenance_obj = ProductStore.objects.get(product=detail_obj.product,
                                                                         subsidiary_store=subsidiary_store_maintenance_obj)
                kardex_input(product_store_maintenance_obj.id, quantity,
                             detail_obj.product.calculate_minimum_price_sale(),
                             ball_change_obj=ball_change_obj)
            except ProductStore.DoesNotExist:
                product_store_maintenance_obj = ProductStore(
                    product=detail_obj.product,
                    subsidiary_store=subsidiary_store_maintenance_obj,
                    stock=quantity
                )
                product_store_maintenance_obj.save()
                kardex_initial(product_store_maintenance_obj, quantity,
                               detail_obj.product.calculate_minimum_price_sale(),
                               ball_change_obj=ball_change_obj)

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': get_dict_orders(client_obj=detail_obj.order.client, is_pdf=False, start_date=start_date,
                                    end_date=end_date),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def generate_receipt(request):
    truck_set = Truck.objects.exclude(truck_model__name__in=['INTER', 'VOLVO'])
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    SubsidiaryStore_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()
    product_store_set = ProductStore.objects.filter(subsidiary_store=SubsidiaryStore_obj)
    products_set = Product.objects.filter(productstore__in=product_store_set)
    clients = Client.objects.all()

    return render(request, 'sales/receipt_random.html', {
        'trucks': truck_set,
        'products_set': products_set,
        'clients': clients
    })


def get_supplies_view(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='I').first()
    product_store_set = ProductStore.objects.filter(subsidiary_store=subsidiary_store_obj)
    products_supplies_set = Product.objects.filter(productstore__in=product_store_set,
                                                   is_supply=True)

    return render(request, 'sales/report_stock_product_supplies_grid.html', {
        'products_supplies_set': products_supplies_set,
    })


def PerceptronList(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        clients_set = Client.objects.filter(clienttype__document_type='06')
        orders = Order.objects.all()
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d %H:%M:%S")
        truck_Set = Truck.objects.all()

        return render(request, 'sales/new_perceptron.html', {
            'orders': orders,
            'clients': clients_set,
            'date': formatdate
        })


def get_stock_product_store(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj)
    truck_set = Truck.objects.filter(subsidiary=subsidiary_obj, drive_type='R')
    product_set = Product.objects.all()
    # dic_stock = ['num':valor]
    dic_stock = {}
    for p in product_set.all():
        stock_ = ProductStore.objects.filter(product__id=p.id,
                                             subsidiary_store__subsidiary=subsidiary_obj).aggregate(
            Sum('stock'))
        # row = {
        #     p.id: stock_['stock__sum'],
        # }s
        dic_stock[p.id] = stock_['stock__sum']
        # dic_stock.append(row)
        # dic_stock[p.id] = {'id': p.id, 'name': p.name, 'stock': stock_['stock__sum']}
    distribution_dictionary = []
    tid = {"B5": 0, "B10": 0, "B15": 0, "B45": 0}
    for t in truck_set.all():
        truck_obj = Truck.objects.get(id=int(t.id))
        distribution_list = DistributionMobil.objects.filter(status='F', truck=truck_obj,
                                                             subsidiary=subsidiary_obj).aggregate(Max('id'))

        if distribution_list['id__max'] is not None:
            distribution_mobil_obj = DistributionMobil.objects.get(id=int(distribution_list['id__max']))
            new = {
                'id_m': distribution_mobil_obj.id,
                'truck': distribution_mobil_obj.truck.license_plate,
                'pilot': distribution_mobil_obj.pilot.full_name(),
                'distribution': [],
            }
            details_list = DistributionDetail.objects.filter(status='C', distribution_mobil=distribution_mobil_obj)
            if details_list.exists():
                for dt_dist in details_list.all():
                    details_mobil = {
                        'id_d': dt_dist.id,
                        'product': dt_dist.product.name,
                        'unit': dt_dist.unit.description,
                        'quantity': dt_dist.quantity,
                    }
                    new.get('distribution').append(details_mobil)
                    if dt_dist.product.code == 'B-10' or dt_dist.product.code == 'F-10':
                        tid['B10'] = tid['B10'] + dt_dist.quantity
                    else:
                        if dt_dist.product.code == 'B-5' or dt_dist.product.code == 'F-5':
                            tid['B5'] = tid['B5'] + dt_dist.quantity
                        else:
                            if dt_dist.product.code == 'B-15' or dt_dist.product.code == 'F-15':
                                tid['B15'] = tid['B15'] + dt_dist.quantity
                            else:
                                if dt_dist.product.code == 'B-45' or dt_dist.product.code == 'F-45':
                                    tid['B45'] = tid['B45'] + dt_dist.quantity

                distribution_dictionary.append(new)

    return render(request, 'sales/report_stock_product_subsidiary.html', {
        'subsidiary_store_set': subsidiary_store_obj,
        'dictionary': distribution_dictionary,
        'dic_stock': dic_stock,
        'tid': tid,
    })


def get_product_recipe_view(request):
    if request.method == 'GET':
        product_pk = request.GET.get('pk', '')
        product_obj = Product.objects.get(id=int(product_pk))
        product_recipe_set = ProductRecipe.objects.filter(product=product_obj)
        products_supplies = Product.objects.filter(is_supply=True)
        unit_set = Unit.objects.all()
        t = loader.get_template('sales/product_recipe_update.html')
        c = ({
            'product_recipe_set': product_recipe_set,
            'products_supplies_set': products_supplies,
            'product_obj': product_obj,
            'unit_set': unit_set,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def delete_recipe(request):
    if request.method == 'GET':
        product_recipe_id = int(request.GET.get('pk', ''))
        product_recipe_obj = ProductRecipe.objects.get(id=product_recipe_id)
        product_recipe_obj.delete()
        return JsonResponse({
            'success': True,
        })


def save_update_recipe(request):
    if request.method == 'GET':
        data = request.GET.get('_details', '')
        registry = json.loads(data)

        product_ins_id = int(registry["_product"])
        product_ins_obj = Product.objects.get(id=product_ins_id)

        _quantity = decimal.Decimal(registry["_quantity"])

        unit_id = int(registry["_unit"])
        unit_obj = Unit.objects.get(id=unit_id)

        _price = decimal.Decimal(registry["_price"])

        product_manufacture_id = int(registry["_product_finality"])
        product_manufacture_obj = Product.objects.get(id=product_manufacture_id)

        try:
            product_recipe_id = int(registry["_id"])
            product_recipe_obj = ProductRecipe.objects.get(id=product_recipe_id)
        except ProductRecipe.DoesNotExist:
            product_recipe_id = 0
        _valor = ''
        _key = 0
        if product_recipe_id == 0:
            recipe_product = {
                'product': product_manufacture_obj,
                'product_input': product_ins_obj,
                'quantity': _quantity,
                'unit': unit_obj,
                'price': _price
            }
            new_recipe_obj = ProductRecipe.objects.create(**recipe_product)
            new_recipe_obj.save()
            _key = new_recipe_obj.id
            _valor = 'Registro ingresado correctamente'
        else:
            product_recipe_obj.product_input = product_ins_obj
            product_recipe_obj.quantity = _quantity
            product_recipe_obj.unit = unit_obj
            product_recipe_obj.price = _price
            product_recipe_obj.save()
            _key = product_recipe_obj.id
            _valor = 'Registro actualizado correctamente'

        return JsonResponse({
            'success': True,
            'key': _key,
            'message': _valor,
        }, status=HTTPStatus.OK)


def new_massiel_payment(request):
    if request.method == 'POST':
        client_orders = int(request.POST.get('client_orders'))  # client_orders
        order_indexes = str(request.POST.get('order_indexes'))  # order_indexes
        order_indexes = order_indexes.replace(']', '').replace('[', '')
        _arr = order_indexes.split(",")
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        payment = 0

        _operation_date = request.POST.get('date_return_loan0', '')
        if not validate(_operation_date):
            data = {'error': "Seleccione fecha."}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if len(request.POST.get('loan_payment', '')) > 0:
            massive_payment = decimal.Decimal(request.POST.get('loan_payment'))  # massive_payment
            transaction_payment_type = str(request.POST.get('transaction_payment_type'))
            number_of_vouchers = 0
            if request.POST.get('number_of_vouchers', '0') != '':
                number_of_vouchers = decimal.Decimal(request.POST.get('number_of_vouchers', '0'))
            code_operation = str(request.POST.get('code_operation'))
            cash_obj = None
            cash_flow_date = ''
            cash_flow_type = ''
            cash_flow_description = ''
            if transaction_payment_type == 'D':
                cash_flow_description = str(request.POST.get('description_deposit'))
                cash_flow_type = 'D'
                cash_flow_date = str(request.POST.get('id_date_deposit'))
                cash_id = str(request.POST.get('id_cash_deposit'))
                cash_obj = Cash.objects.get(id=cash_id)
            elif transaction_payment_type == 'E':
                cash_flow_date = str(request.POST.get('id_date'))
                cash_flow_description = str(request.POST.get('id_description'))
                cash_flow_type = 'E'
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
            elif transaction_payment_type == 'F':
                cash_flow_description = str(request.POST.get('id_description_deposit_fise'))
                cash_flow_date = str(request.POST.get('id_date_desposit_fise'))
                cash_id = str(request.POST.get('id_cash_deposit_fise'))
                cash_obj = Cash.objects.get(id=cash_id)
                cash_flow_type = 'D'

            for a in _arr:
                order_obj = Order.objects.get(id=int(a))
                detail_with_unit_g_set = order_obj.orderdetail_set.filter(Q(unit__name='G') | Q(unit__name='GBC'))
                for da in detail_with_unit_g_set:
                    # if da.repay_loan() == 0:
                    payment = da.multiply() - da.repay_loan()
                    massive_payment = massive_payment - payment
                    save_loan_payment_in_cash_flow(
                        cash_obj=cash_obj,
                        user_obj=user_obj,
                        order_obj=order_obj,
                        order_detail=da,
                        cash_flow_date=cash_flow_date,
                        cash_flow_type=cash_flow_type,
                        cash_flow_operation_code=code_operation,
                        cash_flow_total=payment,
                        cash_flow_description=(cash_flow_description + ' | IMPORTE: {}').format(str(payment)),
                        loan_payment_quantity=0,
                        loan_payment_operation_date=_operation_date,
                        transaction_payment_number_of_vouchers=number_of_vouchers,
                        transaction_payment_type=transaction_payment_type,
                    )
            client_obj = Client.objects.get(id=client_orders)

            return JsonResponse({
                'success': True,
                'message': 'El cliente se asocio correctamente.',
                'grid': get_dict_orders(client_obj=client_obj, is_pdf=False, start_date=None, end_date=None),
            })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def save_loan_payment_in_cash_flow(
        cash_obj=None,
        user_obj=None,
        order_obj=None,
        order_detail=None,
        requirement_buys_obj=None,
        requirement_detail_buys_obj=None,
        cash_flow_date='',
        cash_flow_type='',
        cash_flow_operation_code='',
        cash_flow_total=0,
        cash_flow_description='',
        loan_payment_quantity=0,
        loan_payment_type='',
        loan_payment_operation_date='',
        transaction_payment_number_of_vouchers=0,
        transaction_payment_type='',
):
    cash_flow_obj = CashFlow(
        transaction_date=cash_flow_date,
        document_type_attached='O',
        description=cash_flow_description,
        order=order_obj,
        type=cash_flow_type,
        operation_code=cash_flow_operation_code,
        requirement_buys=requirement_buys_obj,
        total=cash_flow_total,
        cash=cash_obj,
        user=user_obj
    )
    cash_flow_obj.save()

    _product = None
    if order_detail is not None:
        _product = order_detail.product
    elif requirement_detail_buys_obj is not None:
        _product = requirement_detail_buys_obj.product

    loan_payment_obj = LoanPayment(
        price=cash_flow_total,
        quantity=loan_payment_quantity,
        type=loan_payment_type,
        product=_product,
        order_detail=order_detail,
        requirement_detail_buys=requirement_detail_buys_obj,
        operation_date=loan_payment_operation_date
    )
    loan_payment_obj.save()

    transaction_payment_obj = TransactionPayment(
        payment=cash_flow_total,
        number_of_vouchers=transaction_payment_number_of_vouchers,
        type=transaction_payment_type,
        operation_code=cash_flow_operation_code,
        loan_payment=loan_payment_obj
    )
    transaction_payment_obj.save()


def get_massiel_payment_form(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        massive_payment = request.GET.get('massive_payment', '')
        massive_return = request.GET.get('massive_return', '')
        client_orders = request.GET.get('client_orders', '')
        order_indexes = request.GET.get('order_indexes', '')
        massive_type = request.GET.get('massive_type', '')

        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')

        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        tpl = None
        context = ()
        if massive_type == 'MP':
            tpl = loader.get_template('sales/new_massiel_payment_form.html')
            context = ({
                'choices_payments': TransactionPayment._meta.get_field('type').choices,
                'massive_payment': massive_payment,
                'order_indexes': order_indexes,
                'client_orders': client_orders,
                'choices_account': cash_set,
                'choices_account_bank': cash_deposit_set,
                'date': formatdate
            })
        elif massive_type == 'MR':
            tpl = loader.get_template('sales/new_massiel_return_form.html')
            context = ({
                'massive_return': massive_return,
                'order_indexes': order_indexes,
                'client_orders': client_orders,
                'date': formatdate
            })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def new_massiel_return(request):
    if request.method == 'POST':
        client_orders = int(request.POST.get('client_orders'))  # client_orders
        order_indexes = str(request.POST.get('order_indexes'))  # order_indexes
        order_indexes = order_indexes.replace(']', '').replace('[', '')
        _arr = order_indexes.split(",")
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        _operation_date = request.POST.get('date_return_loan0', '')
        if not validate(_operation_date):
            data = {'error': "Seleccione fecha."}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if len(request.POST.get('loan_quantity', '')) > 0:
            massive_return = decimal.Decimal(request.POST.get('loan_quantity'))  # massive_return

            for a in _arr:
                order_obj = Order.objects.get(id=int(a))
                detail_with_unit_ball_set = order_obj.orderdetail_set.filter(unit__name='B')

                for da in detail_with_unit_ball_set:
                    quantity = da.quantity_sold
                    loan_payment_obj = LoanPayment(
                        price=da.price_unit,
                        quantity=quantity,
                        product=da.product,
                        order_detail=da,
                        operation_date=_operation_date
                    )
                    loan_payment_obj.save()
                    if order_obj.type == 'V':
                        product_supply_obj = get_iron_man(da.product.id)
                        subsidiary_store_supply_obj = SubsidiaryStore.objects.get(
                            subsidiary=da.order.subsidiary_store.subsidiary, category='I')
                        try:
                            product_store_supply_obj = ProductStore.objects.get(product=product_supply_obj,
                                                                                subsidiary_store=subsidiary_store_supply_obj)
                            kardex_input(product_store_supply_obj.id, quantity,
                                         product_supply_obj.calculate_minimum_price_sale(),
                                         loan_payment_obj=loan_payment_obj)
                        except ProductStore.DoesNotExist:
                            product_store_supply_obj = ProductStore(
                                product=product_supply_obj,
                                subsidiary_store=subsidiary_store_supply_obj,
                                stock=quantity
                            )
                            product_store_supply_obj.save()
                            kardex_initial(product_store_supply_obj, quantity,
                                           product_supply_obj.calculate_minimum_price_sale(),
                                           loan_payment_obj=loan_payment_obj)

                    massive_return = massive_return - quantity

        client_obj = Client.objects.get(id=client_orders)

        return JsonResponse({
            'success': True,
            'message': 'El cliente se asocio correctamente.',
            'grid': get_dict_orders(client_obj=client_obj, is_pdf=False, start_date=None, end_date=None),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_stock_product_store_all(request):
    dictionary_total = []
    dictionary_loan_payment = []
    stock_v = 0
    stock_i = 0
    stock_m = 0
    stock_r = 0
    stock_g = 0
    stock_o = 0
    _count = Product.objects.all().count()
    total_payment_b = 0
    total_detail_b = 0
    for p in Product.objects.all():
        _stock_v = ProductStore.objects.filter(subsidiary_store__category='V', product__id=p.id).aggregate(Sum('stock'))
        if _stock_v['stock__sum'] is None:
            stock_v = 0
        else:
            stock_v = _stock_v['stock__sum']
        _stock_i = ProductStore.objects.filter(subsidiary_store__category='I', product__id=p.id).aggregate(Sum('stock'))
        if _stock_i['stock__sum'] is None:
            stock_i = 0
        else:
            stock_i = _stock_i['stock__sum']
        _stock_m = ProductStore.objects.filter(subsidiary_store__category='M', product__id=p.id).aggregate(Sum('stock'))
        if _stock_m['stock__sum'] is None:
            stock_m = 0
        else:
            stock_m = _stock_m['stock__sum']
        _stock_r = ProductStore.objects.filter(subsidiary_store__category='R', product__id=p.id).aggregate(Sum('stock'))
        if _stock_r['stock__sum'] is None:
            stock_r = 0
        else:
            stock_r = _stock_r['stock__sum']
        _stock_g = ProductStore.objects.filter(subsidiary_store__category='G', product__id=p.id).aggregate(Sum('stock'))
        if _stock_g['stock__sum'] is None:
            stock_g = 0
        else:
            stock_g = _stock_g['stock__sum']
        _stock_o = ProductStore.objects.filter(subsidiary_store__category='O', product__id=p.id).aggregate(Sum('stock'))
        if _stock_o['stock__sum'] is None:
            stock_o = 0
        else:
            stock_o = _stock_o['stock__sum']
        total_order_detail = OrderDetail.objects.filter(product__id=p.id, status='V', unit_id=4).aggregate(
            Sum('quantity_sold'))
        payment_p = LoanPayment.objects.filter(product__id=p.id, type='V').aggregate(Sum('quantity'))
        if payment_p['quantity__sum'] is not None and total_order_detail['quantity_sold__sum'] is not None:
            total_payment_b = payment_p['quantity__sum']
            total_detail_b = total_order_detail['quantity_sold__sum']
        new = {
            'product_name': p.name,
            'quantity': _count,
            'stock_v': stock_v,
            'stock_i': stock_i,
            'stock_m': stock_m,
            'stock_r': stock_r,
            'stock_g': stock_g,
            'stock_o': stock_o,
            'total_b': total_detail_b - total_payment_b,
        }
        dictionary_total.append(new)

    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    truck_set = Truck.objects.filter(drive_type='R')
    product_set = Product.objects.all()
    dic_stock = {}
    for p in product_set.all():
        stock_ = ProductStore.objects.filter(product__id=p.id).aggregate(
            Sum('stock'))
        dic_stock[p.id] = stock_['stock__sum']
    distribution_dictionary = []
    tid = {"B5": 0, "B10": 0, "B15": 0, "B45": 0}
    for t in truck_set.all():
        truck_obj = Truck.objects.get(id=int(t.id))
        distribution_list = DistributionMobil.objects.filter(status='F', truck=truck_obj).aggregate(Max('id'))

        if distribution_list['id__max'] is not None:
            distribution_mobil_obj = DistributionMobil.objects.get(id=int(distribution_list['id__max']))
            new = {
                'id_m': distribution_mobil_obj.id,
                'truck': distribution_mobil_obj.truck.license_plate,
                'pilot': distribution_mobil_obj.pilot.full_name(),
                'distribution': [],
            }
            details_list = DistributionDetail.objects.filter(status='C', distribution_mobil=distribution_mobil_obj)
            if details_list.exists():
                for dt_dist in details_list.all():
                    details_mobil = {
                        'id_d': dt_dist.id,
                        'product': dt_dist.product.name,
                        'unit': dt_dist.unit.description,
                        'quantity': dt_dist.quantity,
                    }
                    new.get('distribution').append(details_mobil)
                    if dt_dist.product.code == 'B-10' or dt_dist.product.code == 'F-10':
                        tid['B10'] = tid['B10'] + dt_dist.quantity
                    else:
                        if dt_dist.product.code == 'B-5' or dt_dist.product.code == 'F-5':
                            tid['B5'] = tid['B5'] + dt_dist.quantity
                        else:
                            if dt_dist.product.code == 'B-15' or dt_dist.product.code == 'F-15':
                                tid['B15'] = tid['B15'] + dt_dist.quantity
                            else:
                                if dt_dist.product.code == 'B-45' or dt_dist.product.code == 'F-45':
                                    tid['B45'] = tid['B45'] + dt_dist.quantity

                distribution_dictionary.append(new)

    return render(request, 'sales/report_stock_product_all.html', {
        'dictionary': distribution_dictionary,
        'dictionary_loan_payment': dictionary_loan_payment,
        'dictionary_total': dictionary_total,
        'dic_stock': dic_stock,
        'tid': tid,
    })


def purchases_of_clients(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    clients = Client.objects.filter(clientassociate__subsidiary=subsidiary_obj)

    if request.method == 'GET':

        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/purchases_of_clients.html', {'formatdate': formatdate, 'clients': clients, })
    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))

        id_client = int(request.POST.get('client'))
        client_obj = Client.objects.get(id=id_client)

        orders = Order.objects.filter(client=client_obj)

        by_units = str(request.POST.get('by-units', 'NO-UNIT'))

        if start_date == end_date:
            orders = orders.filter(create_at__date=start_date, type__in=['V', 'R'])
        else:
            orders = orders.filter(create_at__date__range=[start_date, end_date], type__in=['V', 'R'])
        if orders:
            if by_units == 'NO-UNIT':
                return JsonResponse({
                    'grid': get_dict_order_queries(orders, is_pdf=False, is_unit=False),
                }, status=HTTPStatus.OK)
            elif by_units == 'UNIT':
                return JsonResponse({
                    'grid': get_dict_order_by_units(orders, is_pdf=False, is_unit=True),
                }, status=HTTPStatus.OK)
        else:
            data = {'error': "No hay operaciones registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_stock_glp(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    product = Product.objects.filter(is_enabled=True, is_approved_by_osinergmin=True, is_supply=True)

    return render(request, 'sales/stock_glp_pluspetrol_and_subsidiary.html', {
        'product': product,
        'subsidiary_obj': subsidiary_obj,
    })


def get_repay_loan(order_detail_id=0):
    response = 0
    loan_payment_set = LoanPayment.objects.filter(
        order_detail__id=order_detail_id, quantity=0
    ).values('order_detail').annotate(totals=Sum('price'))
    if loan_payment_set.count() > 0:
        response = loan_payment_set[0].get('totals')
    return response


def get_return_loan(order_detail_id=0):
    response = 0
    loan_payment_set = LoanPayment.objects.filter(
        order_detail__id=order_detail_id
    ).values('order_detail').annotate(totals=Sum('quantity'))
    if loan_payment_set.count() > 0:
        response = loan_payment_set[0].get('totals')
    return response


def get_total_remaining_repay_loan(order_id=0):
    response = 0
    order_detail_set = OrderDetail.objects.filter(
        order__id=order_id, order__type__in=['R', 'V']
    ).values('id', 'quantity_sold', 'price_unit', 'unit__name')
    for d in order_detail_set:
        if d['unit__name'] == 'G' or d['unit__name'] == 'GBC':
            response = response + ((d['quantity_sold'] * d['price_unit']) - get_repay_loan(d['id']))
    return response


def get_total_remaining_return_loan(order_id=0):
    response = 0
    order_detail_set = OrderDetail.objects.filter(
        order__id=order_id, order__type__in=['R', 'V']
    ).values('id', 'quantity_sold', 'price_unit', 'unit__name')
    for d in order_detail_set:
        if d['unit__name'] == 'B':
            response = response + (d['quantity_sold'] - get_return_loan(d['id']))
    return response


def get_summary_debtors(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        subsidiary_set = Subsidiary.objects.all()

        return render(request, 'sales/summary_of_debtors.html', {
            'formatdate': formatdate,
            'subsidiary_set': subsidiary_set
        })
    elif request.method == 'POST':
        id_subsidiary = int(request.POST.get('subsidiary'))
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        _days = (end - start).days + 1
        date_generated = [start + timedelta(days=x) for x in range(0, _days)]
        all_orders = []

        if id_subsidiary == 1000:
            subsidiary_set = Subsidiary.objects.all().values('id', 'name')
        else:
            subsidiary_set = Subsidiary.objects.filter(id=id_subsidiary).values('id', 'name')

        for s in subsidiary_set:
            arr_subsidiary = {
                'subsidiary_id': s['id'],
                'subsidiary_name': s['name'],
                'clients': [],
                'summary_loans': [],
                'nro_clients': 0,
                'summary_repay_loan_in_clients': '',
                'summary_return_loan_in_clients': '',
            }

            client_set = Client.objects.filter(
                clientassociate__subsidiary_id=s['id']
            ).order_by('names').values('id', 'names')
            _summary_repay_loan_in_clients = 0
            _summary_return_loan_in_clients = 0

            date_dict = {}

            for c in client_set:
                arr_client = {
                    'client_id': c['id'],
                    'client_names': c['names'],
                    'dates': [],
                    'days': _days,
                    'summary_repay_loan_in_dates': '',
                    'summary_return_loan_in_dates': '',
                    'cumulative_remaining_repay_loan': 0,
                    'cumulative_remaining_return_loan': 0,
                }

                order_cumulative_set = Order.objects.filter(
                    client=c['id'], create_at__date__lt=start, type__in=['V', 'R']
                ).order_by('id').values('id', 'total')

                cmr_repay_loan = 0
                cmr_return_loan = 0
                for oc in order_cumulative_set:
                    cmr_repay_loan = cmr_repay_loan + get_total_remaining_repay_loan(oc['id'])
                    cmr_return_loan = cmr_return_loan + get_total_remaining_return_loan(oc['id'])

                arr_client['cumulative_remaining_repay_loan'] = cmr_repay_loan
                arr_client['cumulative_remaining_return_loan'] = cmr_return_loan

                _summary_repay_loan = 0
                _summary_return_loan = 0
                for date in date_generated:
                    arr_date = {
                        'date': date,
                        'orders': [],
                        'total_repay_loan_in_orders': arr_client['cumulative_remaining_repay_loan'],
                        'total_return_loan_in_orders': arr_client['cumulative_remaining_return_loan'],
                    }

                    order_set = Order.objects.filter(
                        client=c['id'], create_at__date=date.strftime("%Y-%m-%d"), type__in=['V', 'R']
                    ).order_by('id').values('id', 'total')

                    _rpl_in_orders = 0
                    _rtl_in_orders = 0

                    for o in order_set:
                        _rpl_in_order = get_total_remaining_repay_loan(o['id'])
                        _rtl_in_order = get_total_remaining_return_loan(o['id'])
                        if _rpl_in_order > 0:
                            _rpl_in_orders = _rpl_in_orders + _rpl_in_order
                        if _rtl_in_order > 0:
                            _rtl_in_orders = _rtl_in_orders + _rtl_in_order

                        arr_order = {
                            'order_id': o['id'],
                            'order_total': str(round(o['total'])),
                            'repay_loan': _rpl_in_order,
                            'return_loan': _rtl_in_order,
                        }
                        arr_date.get('orders').append(arr_order)

                    arr_date['total_repay_loan_in_orders'] = str(
                        round((arr_date['total_repay_loan_in_orders'] + _rpl_in_orders), 2))
                    arr_date['total_return_loan_in_orders'] = str(
                        round(arr_date['total_return_loan_in_orders'] + _rtl_in_orders))

                    arr_client['cumulative_remaining_repay_loan'] = arr_client[
                                                                        'cumulative_remaining_repay_loan'] + _rpl_in_orders
                    arr_client['cumulative_remaining_return_loan'] = arr_client[
                                                                         'cumulative_remaining_return_loan'] + _rtl_in_orders

                    _summary_repay_loan = _summary_repay_loan + _rpl_in_orders
                    _summary_return_loan = _summary_return_loan + _rtl_in_orders

                    _search_value = date.day
                    if _search_value in date_dict.keys():
                        _day = date_dict[_search_value]
                        _rpl = _day.get('rpl')
                        _rl = _day.get('rl')
                        date_dict[_search_value]['rpl'] = _rpl + _rpl_in_orders + decimal.Decimal(
                            arr_date['total_repay_loan_in_orders'])
                        date_dict[_search_value]['rl'] = _rl + _rtl_in_orders + decimal.Decimal(
                            arr_date['total_return_loan_in_orders'])
                    else:
                        date_dict[_search_value] = {'rpl': 0, 'rl': 0}

                    arr_client.get('dates').append(arr_date)

                arr_client['summary_repay_loan_in_dates'] = str(round(_summary_repay_loan, 2))
                arr_client['summary_return_loan_in_dates'] = str(round(_summary_return_loan))
                arr_subsidiary.get('clients').append(arr_client)
                arr_subsidiary['nro_clients'] = len(arr_subsidiary.get('clients')) + 1

                _summary_repay_loan_in_clients = _summary_repay_loan_in_clients + _summary_repay_loan
                _summary_return_loan_in_clients = _summary_return_loan_in_clients + _summary_return_loan

            arr_subsidiary['summary_repay_loan_in_clients'] = str(round(_summary_repay_loan_in_clients, 2))
            arr_subsidiary['summary_return_loan_in_clients'] = str(round(_summary_return_loan_in_clients))
            arr_subsidiary.get('summary_loans').append(date_dict)
            all_orders.append(arr_subsidiary)

        tpl = loader.get_template('sales/summary_of_debtors_grid_list.html')

        context = (
            {'date_generated': date_generated, 'all_orders': all_orders, })

        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_report_sales_subsidiary(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        if pk != '':
            dates_request = request.GET.get('dates', '')
            data_dates = json.loads(dates_request)
            date_initial = (data_dates["date_initial"])
            date_final = (data_dates["date_final"])
            pk_subsidiary = (data_dates["subsidiary"])
            array1 = []
            array2 = []
            array3 = []
            array4 = []
            array5 = []
            array6 = []
            array_district = []
            sales_subsidiary = []
            purchase_subsidiary = []
            cash_pay_subsidiary = []
            payment_subsidiary = []
            array_p_p = []
            v1 = "label"
            v2 = "y"
            subsidiary_set = None
            sales_vs_expenses_set = None
            if pk_subsidiary == '0':
                subsidiary_set = Subsidiary.objects.all()
                print(date_initial)
                print(date_final)
                sales_vs_expenses_set = get_sales_vs_expenses(subsidiary_obj=None, start_date=date_initial,
                                                              end_date=date_final)
            else:
                subsidiary_set = Subsidiary.objects.filter(id=int(pk_subsidiary))
                sales_vs_expenses_set = get_sales_vs_expenses(subsidiary_obj=subsidiary_set.first(),
                                                              start_date=date_initial, end_date=date_final)
            print(sales_vs_expenses_set)
            for s in subsidiary_set:
                t = Order.objects.filter(
                    subsidiary_store__subsidiary_id=s.id,
                    create_at__date__range=(date_initial, date_final), type__in=['V', 'R']
                ).aggregate(r=Coalesce(Sum('total'), 0))
                sales_dict = {
                    v1: s.name,
                    v2: float(t['r'])
                }
                array1.append(sales_dict)
                c = CashFlow.objects.filter(
                    cash__subsidiary_id=s.id,
                    type='E',
                    transaction_date__range=(date_initial, date_final)
                ).aggregate(r=Coalesce(Sum('total'), 0))
                cash_dict = {
                    v1: s.name,
                    v2: float(c['r'])
                }
                array2.append(cash_dict)

                # ----------------ventas ------------------
                sales = {
                    'subsidiary': s.name,
                    'set': []
                }
                subsidiary_sales = []
                order_set = Order.objects.filter(
                    subsidiary_store__subsidiary_id=s.id,
                    create_at__range=(date_initial, date_final), type__in=['V', 'R']
                ).values('create_at').annotate(totales=Sum('total'))
                for vt in order_set:
                    sales_t = {
                        # 'x': 'new Date(' + str(vt['create_at'].strftime("%Y, %m, %d")) + ')',
                        'x': vt['create_at'],
                        'y': str(vt['totales'])
                    }
                    subsidiary_sales.append(sales_t)
                sales['subsidiary'] = s.name

                sales['set'] = subsidiary_sales
                sales_subsidiary.append(sales)

                # ---------------Payments-------------------
                payments = {
                    'subsidiary': s.name,
                    'set': []
                }
                subsidiary_payment = []
                cashflow_set = CashFlow.objects.filter(
                    cash__subsidiary_id=s.id, type='E',
                    transaction_date__range=(date_initial, date_final)
                ).values('transaction_date').annotate(totales=Sum('total')).order_by('transaction_date')
                for pt in cashflow_set:
                    payment_t = {
                        'x': pt['transaction_date'],
                        'y': str(pt['totales'])
                    }
                    subsidiary_payment.append(payment_t)
                payments['subsidiary'] = s.name
                payments['set'] = subsidiary_payment
                payment_subsidiary.append(payments)

                # ----------COMPRAS VS PAGOS----------
                p = PurchaseDetail.objects.filter(
                    purchase__subsidiary_id=s.id, purchase__status='A',
                    purchase__purchase_date__range=(date_initial, date_final)
                ).values(
                    'purchase__subsidiary__name'
                ).annotate(total=Sum(F('price_unit') * F('quantity')))

                if p.exists():
                    p_obj = p[0]
                    sum_total = p_obj['total']
                    purchase_dict = {
                        'label': s.name,
                        'y': float(round(sum_total, 2))
                    }
                else:
                    purchase_dict = {
                        'label': s.name,
                        'y': float(0.00)
                    }

                array4.append(purchase_dict)

                # GASTOS
                cs = CashFlow.objects.filter(
                    cash__subsidiary_id=s.id,
                    type='S',
                    cash__currency_type='S',
                    cash_transfer__isnull=True,
                    transaction_date__range=(date_initial, date_final)
                ).aggregate(r=Coalesce(Sum('total'), 0))
                cash_dict = {
                    'label': s.name,
                    'y': float(cs['r'])
                }
                array3.append(cash_dict)

                # -----------Compras(lineal)--------------

                purchase_lineal = {
                    'subsidiary': s.name,
                    'set': []
                }
                subsidiary_purchase = []
                p_l = PurchaseDetail.objects.filter(
                    purchase__subsidiary_id=s.id, purchase__status='A',
                    purchase__purchase_date__range=(date_initial, date_final)
                ).values(
                    'purchase__purchase_date'
                ).annotate(total=Sum(F('price_unit') * F('quantity'))).order_by('purchase__purchase_date')

                for pt in p_l:
                    purchase_t = {
                        # 'x': 'new Date(' + str(vt['create_at'].strftime("%Y, %m, %d")) + ')',
                        'x': pt['purchase__purchase_date'],
                        'y': str(pt['total'])
                    }
                    subsidiary_purchase.append(purchase_t)
                purchase_lineal['subsidiary'] = s.name
                purchase_lineal['set'] = subsidiary_purchase
                purchase_subsidiary.append(purchase_lineal)

                # -----------Pagos(lineal)--------------

                cash_lineal = {
                    'subsidiary': s.name,
                    'set': []
                }
                subsidiary_cash = []
                cash_flow_set = CashFlow.objects.filter(
                    cash__subsidiary_id=s.id,
                    type='S',
                    transaction_date__range=(date_initial, date_final)
                ).values(
                    'transaction_date'
                ).annotate(r=Coalesce(Sum('total'), 0)).order_by('transaction_date')

                for c in cash_flow_set:
                    c_t = {
                        'x': c['transaction_date'],
                        'y': str(c['r'])
                    }
                    subsidiary_cash.append(c_t)

                cash_lineal['subsidiary'] = s.name
                cash_lineal['set'] = subsidiary_cash
                cash_pay_subsidiary.append(cash_lineal)

                # recovered
                distribution_mobil_set = LoanPayment.objects.filter(
                    operation_date__range=[date_initial, date_final],
                    order_detail__order__subsidiary_store__subsidiary_id=s.id
                ).aggregate(r=Coalesce(Sum('quantity'), 0))
                recovered_dict = {
                    'label': s.name,
                    'y': float(distribution_mobil_set['r'])
                }
                array5.append(recovered_dict)

                # borrowed
                order_detail_set = OrderDetail.objects.filter(
                    order__distribution_mobil__date_distribution__range=[date_initial, date_final],
                    order__subsidiary_store__subsidiary_id=s.id,
                    unit__name='B'
                ).aggregate(r=Coalesce(Sum('quantity_sold'), 0))
                borrowed_dict = {
                    'label': s.name,
                    'y': float(order_detail_set['r'])
                }
                array6.append(borrowed_dict)

                # expenses

                '''expenses_set = CashFlow.objects.filter(
                    order__distribution_mobil__date_distribution__range=[date_initial, date_final],
                    order__subsidiary_store__subsidiary_id=s.id,
                    type='S'
                ).values(
                    'order__distribution_mobil__truck__pk',
                    'order__distribution_mobil__truck__license_plate',
                ).annotate(Sum('total'))

                subsidiary_trucks = []'''

                # -------------COMPRAS POR PROVEEDOR------------

                p_p = PurchaseDetail.objects.filter(purchase__subsidiary__id=s.id, purchase__status='A',
                                                    purchase__purchase_date__range=(date_initial, date_final)).values(
                    'purchase__supplier__name').annotate(total=Sum(F('price_unit') * F('quantity'))).order_by('-total')

                if p_p.exists():
                    for st in p_p:
                        suplier_name = st['purchase__supplier__name']
                        total = st['total']
                        purchase_dict = {
                            'label': suplier_name,
                            'y': float(round(total, 2))
                        }
                        array_p_p.append(purchase_dict)
                # else:
                #     purchase_dict = {
                #         'label': 'OTROS',
                #         'y': float(0.00)
                #     }
                # array_p_p.append(purchase_dict)

            # VENTAS POR DISTRITO
            district_ = ''
            for d in Order.objects.filter(create_at__date__range=(date_initial, date_final),
                                          type__in=['V', 'R']).values(
                'client__clientaddress__district__description').annotate(totales=Sum(F('total'))):
                if d['client__clientaddress__district__description'] is None:
                    district_ = 'OTROS'
                else:
                    district_ = str(d['client__clientaddress__district__description'])
                sales_district = {
                    'label': district_,
                    'y': float(d['totales'])
                }
                array_district.append(sales_district)

            tpl = loader.get_template('sales/report_graphic_sales_by_dates.html')
            context = ({
                'sales': sales_subsidiary,
                'payment': payment_subsidiary,
                'sales_total': array1,
                'cash_total': array2,
                'purchase_total': array4,
                'cash_total_purchase': array3,
                'recovered_set': array5,
                'borrowed_set': array6,
                'sales_vs_expenses': sales_vs_expenses_set,
                'purchase_susbsidiary': purchase_subsidiary,
                'cash_pay_subsidiary': cash_pay_subsidiary,
                'array_district': array_district,
                'array_p_p': array_p_p
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
            })
        else:
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            subsidiary_set = Subsidiary.objects.all()
            return render(request, 'sales/report_graphic_sales.html', {
                'date_now': date_now,
                'subsidiary_set': subsidiary_set,
            })


def get_order_sales(pk, date_initial, date_final):
    order_set = Order.objects.filter(subsidiary_store__subsidiary_id=pk,
                                     create_at__range=(
                                         date_initial, date_final), type__in=['V', 'R']).values('create_at').annotate(
        totales=Sum('total'))
    return order_set


def get_cash_payment(pk, date_initial, date_final):
    cash_set = CashFlow.objects.filter(cash__subsidiary_id=pk, type='E',
                                       transaction_date__range=(
                                           date_initial, date_final)).values('transaction_date').annotate(
        totales=Sum('total'))
    return cash_set


def get_order_sales_total(pk, date_initial, date_final):
    totales = Order.objects.filter(subsidiary_store__subsidiary_id=pk,
                                   create_at__range=(
                                       date_initial, date_final), type__in=['V', 'R']).aggregate(Sum('total'))
    return totales['total__sum']


# def get_utc(_date):
#     local_tz = pytz.timezone('America/Bogota')
#     local_dt = _date.replace(tzinfo=pytz.utc).astimezone(local_tz)
#     return local_tz.normalize(local_dt)


def check_review(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        # is_review = False
        order_obj = Order.objects.get(id=pk)
        if order_obj.is_review is False:
            order_obj.is_review = True
            order_obj.save()
        else:
            order_obj.is_review = False
            order_obj.save()

        return JsonResponse({
            'success': True,
        })


def check_review_pay(request):
    if request.method == 'GET':
        lp_id = request.GET.get('lp_id', '')
        loan_payment_obj = LoanPayment.objects.get(id=lp_id)
        if loan_payment_obj.is_check is False:
            loan_payment_obj.is_check = True
            loan_payment_obj.save()
        else:
            loan_payment_obj.is_check = False
            loan_payment_obj.save()

        return JsonResponse({
            'success': True,
        })


def sold_ball_request(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if request.method == 'GET':
        client_id = request.GET.get('client_id', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        order_set = Order.objects.filter(
            create_at__date__range=[start_date, end_date], type__in=['V', 'R'], subsidiary=subsidiary_obj
        )
        if client_id != 'T':
            client_obj = Client.objects.get(pk=int(client_id))
            order_set = order_set.filter(client=client_obj)

        order_set = order_set.prefetch_related(
            Prefetch(
                'orderdetail_set', queryset=OrderDetail.objects.filter(unit__name='B').prefetch_related(
                    Prefetch('loanpayment_set__transactionpayment_set')
                ).select_related('unit', 'product')
            )
        ).select_related('client').order_by('client__names', 'create_at')

        context = get_dict_sold_ball(order_set=order_set, client_obj=None)

        dict_orders = context.get('o_dict')
        sum_quantity = context.get('sum_quantity')
        sum_payment = context.get('sum_payment')

        tpl = loader.get_template('sales/report_sold_ball_grid.html')
        context = ({
            'dict_orders': dict_orders,
            'sum_quantity': sum_quantity,
            'sum_payment': sum_payment,
        })
        return JsonResponse({
            'success': True,
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def sold_ball(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        clients = Client.objects.filter(clientassociate__subsidiary=subsidiary_obj)

        return render(request, 'sales/report_sold_ball.html', {
            'clients': clients,
            'formatdate': formatdate,
        })


def get_dict_sold_ball(order_set, client_obj=None):
    o_dict = []
    sum_quantity = 0
    sum_payment = 0
    for o in order_set:
        order_detail_set = o.orderdetail_set.all()

        od_dict = []
        sum_loans = 0

        for od in order_detail_set:
            loan_payment_set = od.loanpayment_set.all()

            lp_dict = []

            for lp in loan_payment_set:
                transaction_payment_set = lp.transactionpayment_set.all()
                if transaction_payment_set.exists():
                    payment = 0
                    transaction_payment_obj = None
                    for t in transaction_payment_set:
                        transaction_payment_obj = t
                        payment = round(transaction_payment_obj.payment, 2)
                    sum_payment += payment
                    sum_quantity += lp.quantity
                    lp_item = {
                        'id': lp.id,
                        'quantity': lp.quantity,
                        'price': lp.price,
                        'discount': lp.discount,
                        'operation_date': lp.operation_date,
                        'transaction_payment_obj': transaction_payment_obj
                    }
                    lp_dict.append(lp_item)
            if len(lp_dict) > 0:
                od_item = {
                    'id': od.id,
                    'product_id': od.product.id,
                    'product_name': od.product.name,
                    'unit_id': od.unit.id,
                    'unit_name': od.unit.name,
                    'quantity_sold': od.quantity_sold,
                    'price_unit': od.price_unit,
                    'subtotal': round(od.price_unit * od.quantity_sold, 2),
                    'loan_payment_dict': lp_dict,
                    'loan_payment_count': len(lp_dict)
                }
                sum_loans += len(lp_dict)
                od_dict.append(od_item)
        if len(od_dict) > 0:
            o_item = {
                'id': o.id,
                'client_names': o.client.names,
                'create_at': o.create_at,
                'total': o.total,
                'order_detail_dict': od_dict,
                'order_detail_count': sum_loans,
            }
            o_dict.append(o_item)

    context = ({
        'o_dict': o_dict,
        'sum_quantity': sum_quantity,
        'sum_payment': sum_payment,
    })
    return context


def get_total_order(order_id):
    sum_multiply = 0
    order_detail_obj = OrderDetail.objects.filter(order__id=order_id).values('price_unit', 'quantity_sold')
    for od in order_detail_obj:
        sum_multiply += od['quantity_sold'] * od['price_unit']
    return sum_multiply


def report_payments_by_client(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        return render(request, 'sales/report_payments_by_client.html', {
            'formatdate': formatdate,
        })

    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))

        client_dict = []

        client_set = Client.objects.filter(
            order__isnull=False, order__subsidiary=subsidiary_obj, order__type__in=['V', 'R']
        ).distinct('id').values('id', 'names')

        # loan_payments_group_set = LoanPayment.objects.filter(
        #     operation_date__range=[start_date, end_date],
        #     order_detail__order__client__id__in=[c['id'] for c in client_set]
        # ).values('operation_date').annotate(sum=Sum('price'))
        # print(loan_payments_group_set)

        for c in client_set:

            loan_payments_group = LoanPayment.objects.filter(
                operation_date__range=[start_date, end_date],
                order_detail__order__client__id=c['id']).values('operation_date').annotate(sum=Sum('price'))
            loan_payment_group = []

            order_dict = {}
            loan_payment_count = 0
            for lpg in loan_payments_group:

                loan_payments_set = LoanPayment.objects.filter(
                    operation_date=lpg['operation_date'],
                    order_detail__order__client__id=c['id']).values(
                    'operation_date', 'id', 'order_detail__order__id', 'order_detail__id', 'price', 'is_check'
                )
                has_check = False
                rows = 0
                rows_loans = 0
                lps = []
                loan_payment_dict = []

                for lp in loan_payments_set:

                    if lp['is_check']:
                        has_check = True

                    lps.append(lp['id'])

                    sum_subtotal = 0

                    transaction_payments_set = TransactionPayment.objects.filter(
                        loan_payment__id=lp['id']
                    ).values('id', 'payment', 'type', 'operation_code')

                    order_obj = Order.objects.filter(
                        pk=lp['order_detail__order__id']
                    ).values('id', 'truck__license_plate', 'create_at').first()

                    total_order = get_total_order(order_obj['id'])

                    price_accumulated = 0

                    _search_value = order_obj['id']
                    if _search_value in order_dict.keys():
                        _order = order_dict[_search_value]
                        _occurrences = _order.get('occurrences')
                        _accumulated = _order.get('accumulated')
                        order_dict[_search_value]['occurrences'] = _occurrences + 1
                        order_dict[_search_value]['accumulated'] = _accumulated + lp['price']
                        price_accumulated = _accumulated + lp['price']
                    else:
                        order_dict[_search_value] = {'occurrences': 0, 'accumulated': lp['price'], }
                        price_accumulated = lp['price']

                    order_detail_set = OrderDetail.objects.filter(
                        order__id=lp['order_detail__order__id']
                    ).values('id', 'quantity_sold', 'price_unit', 'unit__id', 'unit__name', 'product__id',
                             'product__name')

                    rows = rows + transaction_payments_set.count()
                    payed = 0
                    for od in order_detail_set:

                        subtotal = od['quantity_sold'] * od['price_unit']
                        sum_subtotal += subtotal

                        has_loan_payment_set = LoanPayment.objects.filter(order_detail__id=od['id'])
                        if has_loan_payment_set.exists():
                            has_loan_payment_obj = has_loan_payment_set.first()
                            price = has_loan_payment_obj.price
                            payed += price

                    transaction_count = transaction_payments_set.count()
                    if transaction_count == 0:
                        transaction_count = 1
                        rows = rows + 1

                    item_loan = {
                        'id': lp['id'],
                        'price': lp['price'],
                        'transaction': transaction_payments_set,
                        'transaction_count': transaction_count,
                        'sum_subtotal': sum_subtotal,
                        'operation_date': lp['operation_date'],
                        'payed': payed,
                        'total_order': total_order,
                        'pending': total_order - price_accumulated,
                        'order_detail_set': order_detail_set,
                        'order_obj': order_obj,
                        'price_accumulated': price_accumulated,
                    }
                    loan_payment_dict.append(item_loan)

                if rows == 0:
                    rows = 1

                loan_payment_count = loan_payment_count + rows

                loan_payment_group.append({
                    'date': lpg['operation_date'],
                    'loan_payment_dict': loan_payment_dict,
                    'loan_payment_count': len(loan_payment_dict),
                    'sum': '{:,}'.format(round(lpg['sum'], 2)),  # Agrupado de pagos por fecha
                    'rows': rows,
                    'orders': len(order_dict),
                    'lps': lps,
                    'check': has_check
                })

            # loan_payment_count = len(loan_payment_group)
            if loan_payments_group.exists():
                client_item = {
                    'client_id': c['id'],
                    'client_names': c['names'],
                    'loan_payment_group': loan_payment_group,
                    'loan_payment_count': loan_payment_count
                }
                client_dict.append(client_item)

        tpl = loader.get_template('sales/report_payments_by_client_grid.html')
        context = ({
            'client_dict': client_dict,
            # 'loan_payments_group_set': loan_payments_group_set,
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def report_ball_all_mass(request):
    products_in_ball = [1, 12, 2, 3]  # BALONES
    products_in_ball_names = ['BALON DE 10 KG', 'BALON DE 15 KG', 'BALON DE 5KG', 'BALON DE 45 KG']  # BALONES
    products_in_iron = [5, 11, 6, 7]  # FIERROS
    products_in_iron_names = ['FIERRO DE 10 KG ', 'FIERRO DE 15KG', 'FIERRO DE 5 KG', 'FIERRO DE 45 KG']  # FIERROS
    sum_ball_5 = 0
    sum_ball_10 = 0
    sum_ball_15 = 0
    sum_ball_45 = 0
    sum_iron_5 = 0
    sum_iron_10 = 0
    sum_iron_15 = 0
    sum_iron_45 = 0
    sum_ball_loan_5 = 0
    sum_ball_loan_10 = 0
    sum_ball_loan_15 = 0
    sum_ball_loan_45 = 0
    sum_route_void_5 = 0
    sum_route_void_10 = 0
    sum_route_void_15 = 0
    sum_route_void_45 = 0
    sum_route_filled_5 = 0
    sum_route_filled_10 = 0
    sum_route_filled_15 = 0
    sum_route_filled_45 = 0
    sum_car_void_5 = 0
    sum_car_void_10 = 0
    sum_car_void_15 = 0
    sum_car_void_45 = 0
    sum_car_filled_5 = 0
    sum_car_filled_10 = 0
    sum_car_filled_15 = 0
    sum_car_filled_45 = 0
    sum_total_ball_5 = 0
    sum_total_ball_10 = 0
    sum_total_ball_15 = 0
    sum_total_ball_45 = 0

    subsidiaries_dict = []

    subsidiaries = [1, 2, 3, 4, 6]

    balls = {}

    queryset = DistributionMobil.objects \
        .filter(subsidiary__id__in=subsidiaries, status='F', distributiondetail__isnull=False) \
        .values('pilot__id', 'subsidiary__id').annotate(max=Max('id'))

    distribution_mobil_set = DistributionMobil.objects.filter(
        id__in=[q['max'] for q in queryset]
    ).select_related('subsidiary').prefetch_related(
        Prefetch(
            'distributiondetail_set',
            queryset=DistributionDetail.objects.filter(
                status='C', type__in=['L', 'V'], product__id__in=products_in_ball
            ).select_related('product').only(
                'id', 'type', 'distribution_mobil', 'quantity', 'product__id', 'product__name')
        )
    ).only('id', 'subsidiary__id', 'subsidiary__name')

    balls_in_distribution = {}

    for dist in distribution_mobil_set:
        for d in dist.distributiondetail_set.all():

            subsidiary_key = dist.subsidiary.id
            if subsidiary_key in balls:
                subsidiary = balls[subsidiary_key]
                ball_dict = subsidiary.get('distributions')
            else:
                ball_dict = {}
                balls[subsidiary_key] = {
                    'subsidiary_id': dist.subsidiary.id,
                    'subsidiary_name': dist.subsidiary.name,
                    'distributions': ball_dict,
                }

            if d.type == 'V':
                if d.product.id == 1:  # BALON DE 10
                    sum_car_void_10 += d.quantity
                elif d.product.id == 12:  # BALON DE 15
                    sum_car_void_15 += d.quantity
                elif d.product.id == 2:  # BALON DE 5
                    sum_car_void_5 += d.quantity
                elif d.product.id == 3:  # BALON DE 45
                    sum_car_void_45 += d.quantity
            elif d.type == 'L':
                if d.product.id == 1:  # BALON DE 10
                    sum_car_filled_10 += d.quantity
                elif d.product.id == 12:  # BALON DE 15
                    sum_car_filled_15 += d.quantity
                elif d.product.id == 2:  # BALON DE 5
                    sum_car_filled_5 += d.quantity
                elif d.product.id == 3:  # BALON DE 45
                    sum_car_filled_45 += d.quantity
            stock_l = 0
            stock_v = 0
            search_value = d.product.id
            if search_value in ball_dict:
                product = ball_dict[search_value]
                if d.type == 'L':
                    stock_l = product.get('distribution_ball_filled')
                    ball_dict[search_value]['distribution_ball_filled'] = stock_l + d.quantity
                elif d.type == 'V':
                    stock_v = product.get('distribution_ball_void')
                    ball_dict[search_value]['distribution_ball_void'] = stock_v + d.quantity
            else:
                if d.type == 'L':
                    stock_l = d.quantity
                elif d.type == 'V':
                    stock_v = d.quantity
                ball_dict[search_value] = {
                    'product_id': d.product.id,
                    'product_name_ball': d.product.name,
                    'product_name_iron': '',
                    'stock_iron': 0,
                    'stock_ball': 0,
                    'ball_loan': 0,
                    'car_ball_filled': 0,
                    'car_ball_void': 0,
                    'distribution_ball_filled': stock_l,
                    'distribution_ball_void': stock_v,
                    'distribution_detail_id': d.id,
                }
            balls[subsidiary_key]['distributions'][search_value] = ball_dict[search_value]

    programming_set = Programming.objects.filter(status='P').prefetch_related(
        Prefetch(
            'route_set',
            queryset=Route.objects.filter(
                type='D', subsidiary__id__in=subsidiaries
            ).select_related('subsidiary').only('id', 'programming__id', 'subsidiary__id', 'subsidiary__name')
        ),
        Prefetch(
            'guide_set', queryset=Guide.objects.prefetch_related(
                # type__in = ('1', 'VACIO(S)'), ('2', 'LLENO(S)')
                Prefetch(
                    'guidedetail_set',
                    queryset=GuideDetail.objects.filter(
                        type__in=[1, 2], product__id__in=products_in_ball
                    ).select_related('product').only(
                        'id', 'guide__id', 'type', 'quantity', 'product__id', 'product__name'
                    )
                )
            ).only('id', 'programming')
        ),
    ).only('id')

    balls_pending_arrival = {}
    for prg in programming_set:

        s = None

        for r in prg.route_set.all():
            s = r.subsidiary

        if s is not None:

            for g in prg.guide_set.all():

                for gd in g.guidedetail_set.all():
                    subsidiary_key = s.id
                    if subsidiary_key in balls:
                        subsidiary = balls[subsidiary_key]
                        ball_dict = subsidiary.get('distributions')
                    else:
                        ball_dict = {}
                        balls[subsidiary_key] = {
                            'subsidiary_id': s.id,
                            'subsidiary_name': s.name,
                            'distributions': ball_dict,
                        }

                    if gd.type == '1':
                        if gd.product.id == 1:  # BALON DE 10
                            sum_route_void_10 += gd.quantity
                        elif gd.product.id == 12:  # BALON DE 15
                            sum_route_void_15 += gd.quantity
                        elif gd.product.id == 2:  # BALON DE 5
                            sum_route_void_5 += gd.quantity
                        elif gd.product.id == 3:  # BALON DE 45
                            sum_route_void_45 += gd.quantity
                    elif gd.type == '2':
                        if gd.product.id == 1:  # BALON DE 10
                            sum_route_filled_10 += gd.quantity
                        elif gd.product.id == 12:  # BALON DE 15
                            sum_route_filled_15 += gd.quantity
                        elif gd.product.id == 2:  # BALON DE 5
                            sum_route_filled_5 += gd.quantity
                        elif gd.product.id == 3:  # BALON DE 45
                            sum_route_filled_45 += gd.quantity
                    stock_void = 0
                    stock_filled = 0
                    search_value = gd.product.id
                    if search_value in ball_dict:
                        product = ball_dict[search_value]
                        if gd.type == '1':
                            stock_void = product.get('car_ball_void')
                            ball_dict[search_value]['car_ball_void'] = stock_void + gd.quantity
                        elif gd.type == '2':
                            stock_filled = product.get('car_ball_filled')
                            ball_dict[search_value]['car_ball_filled'] = stock_filled + gd.quantity
                    else:
                        if gd.type == '1':
                            stock_void = gd.quantity
                        elif gd.type == '2':
                            stock_filled = gd.quantity
                        ball_dict[search_value] = {
                            'product_id': gd.product.id,
                            'product_name_ball': gd.product.name,
                            'product_name_iron': '',
                            'stock_iron': 0,
                            'stock_ball': 0,
                            'ball_loan': 0,
                            'car_ball_filled': stock_filled,
                            'car_ball_void': stock_void,
                            'distribution_ball_filled': 0,
                            'distribution_ball_void': 0,
                            'type': gd.type,
                        }
                    balls[subsidiary_key]['distributions'][search_value] = ball_dict[search_value]

    product_store_in_iron = ProductStore.objects.filter(
        subsidiary_store__category='I',
        subsidiary_store__subsidiary__id__in=subsidiaries,
        product__id__in=products_in_iron
    ).select_related('subsidiary_store__subsidiary', 'product').only(
        'id', 'stock', 'product__id', 'product__name',
        'subsidiary_store__subsidiary__id',
        'subsidiary_store__subsidiary__name',
    )

    balls_in_irons = {}
    for ps in product_store_in_iron:

        subsidiary_key = ps.subsidiary_store.subsidiary.id

        if subsidiary_key in balls:
            subsidiary = balls[subsidiary_key]
            ball_dict = subsidiary.get('distributions')
        else:
            ball_dict = {}
            balls[subsidiary_key] = {
                'subsidiary_id': ps.subsidiary_store.subsidiary.id,
                'subsidiary_name': ps.subsidiary_store.subsidiary.name,
                'distributions': ball_dict,
            }

        if ps.product.id == 5:  # FIERRO DE 10
            sum_iron_10 += ps.stock
        elif ps.product.id == 11:  # FIERRO DE 15
            sum_iron_15 += ps.stock
        elif ps.product.id == 6:  # FIERRO DE 5
            sum_iron_5 += ps.stock
        elif ps.product.id == 7:  # FIERRO DE 45
            sum_iron_45 += ps.stock

        search_value = ps.product.id
        product_name_ball = ''
        if search_value == 5:  # BALON DE 10
            search_value = 1
            product_name_ball = 'BALON DE 10 KG'
        elif search_value == 11:  # BALON DE 15
            search_value = 12
            product_name_ball = 'BALON DE 15 KG'
        elif search_value == 6:  # BALON DE 5
            search_value = 2
            product_name_ball = 'BALON DE 5 KG'
        elif search_value == 7:  # BALON DE 45
            search_value = 3
            product_name_ball = 'BALON DE 45 KG'

        if search_value in ball_dict.keys():
            product = ball_dict[search_value]
            stock = product.get('stock_iron')
            product_name_iron = product.get('product_name_iron')
            ball_dict[search_value]['product_name_iron'] = ps.product.name
            ball_dict[search_value]['stock_iron'] = stock + ps.stock
        else:
            ball_dict[search_value] = {
                'product_id': ps.product.id,
                'product_name_ball': product_name_ball,
                'product_name_iron': ps.product.name,
                'stock_iron': ps.stock,
                'stock_ball': 0,
                'ball_loan': 0,
                'car_ball_filled': 0,
                'car_ball_void': 0,
                'distribution_ball_filled': 0,
                'distribution_ball_void': 0,
            }
        balls[subsidiary_key]['distributions'][search_value] = ball_dict[search_value]

    order_detail_set = OrderDetail.objects.filter(
        order__subsidiary__id__in=subsidiaries, product__id__in=products_in_ball, unit__name='B',
        order__type__in=['R', 'V'],
    ).select_related('order__subsidiary', 'product').prefetch_related(
        Prefetch('loanpayment_set', queryset=LoanPayment.objects.only('id', 'order_detail__id', 'quantity'))
    ).only('id', 'quantity_sold', 'order__subsidiary__id', 'order__subsidiary__name', 'product__id', 'product__name', )

    for od in order_detail_set:
        subsidiary_key = od.order.subsidiary.id

        if subsidiary_key in balls:
            subsidiary = balls[subsidiary_key]
            ball_dict = subsidiary.get('distributions')
        else:
            ball_dict = {}
            balls[subsidiary_key] = {
                'subsidiary_id': od.order.subsidiary.id,
                'subsidiary_name': od.order.subsidiary.name,
                'distributions': ball_dict,
            }

        loan_payment_set = od.loanpayment_set.all()
        ball_loan = 0
        if loan_payment_set.exists():
            ball_loan_total = 0
            ball_total = od.quantity_sold
            for lp in loan_payment_set:
                ball_loan_total = ball_loan_total + lp.quantity
            ball_loan = ball_total - ball_loan_total
        else:
            ball_loan = od.quantity_sold

        if od.product.id == 1:  # BALON DE 10
            sum_ball_loan_10 += ball_loan
        elif od.product.id == 12:  # BALON DE 15
            sum_ball_loan_15 += ball_loan
        elif od.product.id == 2:  # BALON DE 5
            sum_ball_loan_5 += ball_loan
        elif od.product.id == 3:  # BALON DE 45
            sum_ball_loan_45 += ball_loan

        search_value = od.product.id

        if search_value in ball_dict:
            product = ball_dict[search_value]
            old_ball_loan = product.get('ball_loan')
            ball_dict[search_value]['ball_loan'] = old_ball_loan + ball_loan
        else:
            ball_dict[search_value] = {
                'product_id': od.product.id,
                'product_name_ball': od.product.name,
                'product_name_iron': '',
                'stock_iron': 0,
                'stock_ball': 0,
                'ball_loan': ball_loan,
                'car_ball_filled': 0,
                'car_ball_void': 0,
                'distribution_ball_filled': 0,
                'distribution_ball_void': 0,
            }
        balls[subsidiary_key]['distributions'][search_value] = ball_dict[search_value]

    product_store_in_ball = ProductStore.objects.filter(
        subsidiary_store__category='V', subsidiary_store__subsidiary__id__in=subsidiaries,
        product__id__in=products_in_ball
    ).select_related('subsidiary_store__subsidiary', 'product').only(
        'id', 'stock', 'product__id', 'product__name',
        'subsidiary_store__subsidiary__id',
        'subsidiary_store__subsidiary__name',
    )

    for ps in product_store_in_ball:

        subsidiary_key = ps.subsidiary_store.subsidiary.id

        if subsidiary_key in balls:
            subsidiary = balls[subsidiary_key]
            ball_dict = subsidiary.get('distributions')
        else:
            ball_dict = {}
            balls[subsidiary_key] = {
                'subsidiary_id': ps.subsidiary_store.subsidiary.id,
                'subsidiary_name': ps.subsidiary_store.subsidiary.name,
                'distributions': ball_dict,
            }

        search_value = ps.product.id
        if ps.product.id == 1:  # BALON DE 10
            sum_ball_10 += ps.stock
        elif ps.product.id == 12:  # BALON DE 15
            sum_ball_15 += ps.stock
        elif ps.product.id == 2:  # BALON DE 5
            sum_ball_5 += ps.stock
        elif ps.product.id == 3:  # BALON DE 45
            sum_ball_45 += ps.stock

        if search_value in ball_dict:
            product = ball_dict[search_value]
            stock = product.get('stock_ball')
            ball_dict[search_value]['stock_ball'] = stock + ps.stock
        else:
            ball_dict[search_value] = {
                'product_id': ps.product.id,
                'product_name_iron': '',
                'product_name_ball': ps.product.name,
                'stock_iron': 0,
                'stock_ball': ps.stock,
                'ball_loan': 0,
                'car_ball_filled': 0,
                'car_ball_void': 0,
                'distribution_ball_void': 0,
                'distribution_ball_filled': 0,
            }
        balls[subsidiary_key]['distributions'][search_value] = ball_dict[search_value]

    balls_sorted = {}
    for s in subsidiaries:
        distributions_sorted = {}
        for p in products_in_ball:
            if p in balls[s]['distributions']:
                distributions_sorted[p] = balls[s]['distributions'][p]
            else:
                distributions_sorted[p] = {
                    'product_id': p,
                    'stock_iron': 0,
                    'stock_ball': 0,
                    'ball_loan': 0,
                    'car_ball_filled': 0,
                    'car_ball_void': 0,
                    'distribution_ball_filled': 0,
                    'distribution_ball_void': 0,
                }
        balls_sorted[s] = balls[s]
        balls_sorted[s]['distributions'] = distributions_sorted

    sum_total_ball_filled_10 = sum_ball_10 + sum_route_filled_10 + sum_ball_loan_10 + sum_car_filled_10
    sum_total_ball_filled_15 = sum_ball_15 + sum_route_filled_15 + sum_ball_loan_15 + sum_car_filled_15
    sum_total_ball_filled_5 = sum_ball_5 + sum_route_filled_5 + sum_ball_loan_5 + sum_car_filled_5
    sum_total_ball_filled_45 = sum_ball_45 + sum_route_filled_45 + sum_ball_loan_45 + sum_car_filled_45

    sum_total_ball_void_10 = sum_iron_10 + sum_route_void_10 + sum_car_void_10
    sum_total_ball_void_15 = sum_iron_15 + sum_route_void_15 + sum_car_void_15
    sum_total_ball_void_5 = sum_iron_5 + sum_route_void_5 + sum_car_void_5
    sum_total_ball_void_45 = sum_iron_45 + sum_route_void_45 + sum_car_void_45

    sum_total_ball_5 = sum_total_ball_filled_5 + sum_total_ball_void_5
    sum_total_ball_10 = sum_total_ball_filled_10 + sum_total_ball_void_10
    sum_total_ball_15 = sum_total_ball_filled_15 + sum_total_ball_void_15
    sum_total_ball_45 = sum_total_ball_filled_45 + sum_total_ball_void_45

    return render(request, 'sales/report_ball_all_mass.html', {
        'balls': balls_sorted,
        'subsidiaries_dict': subsidiaries_dict,
        'sum_ball_10': sum_ball_10,
        'sum_ball_15': sum_ball_15,
        'sum_ball_5': sum_ball_5,
        'sum_ball_45': sum_ball_45,
        'sum_ball_loan_5': sum_ball_loan_5,
        'sum_ball_loan_10': sum_ball_loan_10,
        'sum_ball_loan_15': sum_ball_loan_15,
        'sum_ball_loan_45': sum_ball_loan_45,
        'sum_iron_10': sum_iron_10,
        'sum_iron_15': sum_iron_15,
        'sum_iron_5': sum_iron_5,
        'sum_iron_45': sum_iron_45,
        'sum_route_void_5': sum_route_void_5,
        'sum_route_void_10': sum_route_void_10,
        'sum_route_void_15': sum_route_void_15,
        'sum_route_void_45': sum_route_void_45,
        'sum_route_filled_5': sum_route_filled_5,
        'sum_route_filled_10': sum_route_filled_10,
        'sum_route_filled_15': sum_route_filled_15,
        'sum_route_filled_45': sum_route_filled_45,
        'sum_car_void_5': sum_car_void_5,
        'sum_car_void_10': sum_car_void_10,
        'sum_car_void_15': sum_car_void_15,
        'sum_car_void_45': sum_car_void_45,
        'sum_car_filled_5': sum_car_filled_5,
        'sum_car_filled_10': sum_car_filled_10,
        'sum_car_filled_15': sum_car_filled_15,
        'sum_car_filled_45': sum_car_filled_45,
        'sum_total_ball_filled_10': sum_total_ball_filled_10,
        'sum_total_ball_filled_15': sum_total_ball_filled_15,
        'sum_total_ball_filled_5': sum_total_ball_filled_5,
        'sum_total_ball_filled_45': sum_total_ball_filled_45,
        'sum_total_ball_void_10': sum_total_ball_void_10,
        'sum_total_ball_void_15': sum_total_ball_void_15,
        'sum_total_ball_void_5': sum_total_ball_void_5,
        'sum_total_ball_void_45': sum_total_ball_void_45,
        'sum_total_ball_5': sum_total_ball_5,
        'sum_total_ball_10': sum_total_ball_10,
        'sum_total_ball_15': sum_total_ball_15,
        'sum_total_ball_45': sum_total_ball_45,
    })


def get_balls_in_car(distribution_detail_set=None, balls_in_car=None):
    sum_ball_5 = 0
    sum_ball_10 = 0
    sum_ball_15 = 0
    sum_ball_45 = 0

    for d in distribution_detail_set:
        key_product = d.product.id

        # print(product_detail_set)

        if key_product in balls_in_car:
            product = balls_in_car[key_product]
            old_quantity = product.get('quantity')
            old_bg_subtotal = product.get('bg_subtotal')
            old_bg_price = product.get('bg_price')
            balls_in_car[key_product]['quantity'] = old_quantity + d.quantity
            balls_in_car[key_product]['bg_subtotal'] = old_bg_subtotal + (old_bg_price * d.quantity)
        else:
            product_detail_set = d.product.rates
            bg_price = get_price_of_product(product_detail_set=product_detail_set, product=d.product, unit=d.unit)
            balls_in_car[key_product] = {
                'product_id': d.product.id,
                'product_name': d.product.name,
                'quantity': d.quantity,
                'bg_price': bg_price,
                'bg_subtotal': bg_price * d.quantity,
                'unit_name': d.unit.name,
            }
        if key_product == 1:  # BALON DE 10
            sum_ball_10 += d.quantity
        elif key_product == 12:  # BALON DE 15
            sum_ball_15 += d.quantity
        elif key_product == 2:  # BALON DE 5
            sum_ball_5 += d.quantity
        elif key_product == 3:  # BALON DE 45
            sum_ball_45 += d.quantity

    sum_ball = sum_ball_10 + sum_ball_5 + sum_ball_15 + sum_ball_45

    context = {
        'balls_in_car': balls_in_car,
        'sum_ball': sum_ball,
        'sum_ball_10': sum_ball_10,
        'sum_ball_5': sum_ball_5,
        'sum_ball_15': sum_ball_15,
        'sum_ball_45': sum_ball_45,
    }

    return context


def get_price_of_product(product_detail_set=None, product=None, unit=None):
    price = 0
    for pd in product_detail_set:
        if pd.product == product and pd.unit == unit:
            price = pd.price_sale
    return price


def status_account(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        products_in_ball = [1, 12, 2, 3]  # BALONES
        sum_total = 0
        acm_sum_5 = 0
        acm_sum_10 = 0
        acm_sum_15 = 0
        acm_sum_45 = 0
        pilot_dict = {}

        # TABLE 1
        queryset = DistributionMobil.objects \
            .filter(subsidiary=subsidiary_obj, status='F', distributiondetail__isnull=False) \
            .values('pilot__id', 'subsidiary__id').annotate(max=Max('id'))

        distribution_mobil_set = DistributionMobil.objects.filter(
            id__in=[q['max'] for q in queryset]
        ).prefetch_related(
            Prefetch(
                'distributiondetail_set',
                queryset=DistributionDetail.objects.filter(
                    status='C', type__in=['L'], quantity__gt=0
                ).select_related('unit', 'product').prefetch_related(
                    Prefetch(
                        'product__productdetail_set',
                        queryset=ProductDetail.objects.select_related('unit'), to_attr='rates'
                    )
                )
            ),  # Prefetch('distributiondetail_set__product__productdetail_set', to_attr='rates')
        ).select_related('pilot').select_related('truck')

        for dm in distribution_mobil_set:
            if dm.distributiondetail_set.all().exists():
                key = dm.pilot.id
                # product_detail_set = dm.rates.all()
                sum_ball = 0
                sum_ball_5 = 0
                sum_ball_10 = 0
                sum_ball_15 = 0
                sum_ball_45 = 0
                if key in pilot_dict:

                    pilot = pilot_dict[key]
                    old_balls_in_car = pilot.get('balls_in_car')
                    old_sum_total = pilot.get('sum_total')
                    old_sum_ball_5 = pilot.get('sum_ball_5')
                    old_sum_ball_10 = pilot.get('sum_ball_10')
                    old_sum_ball_15 = pilot.get('sum_ball_15')
                    old_sum_ball_45 = pilot.get('sum_ball_45')

                    context = get_balls_in_car(
                        distribution_detail_set=dm.distributiondetail_set.all(), balls_in_car=old_balls_in_car
                    )
                    sum_ball = context.get('sum_ball')

                    sum_ball_5 = context.get('sum_ball_5')
                    sum_ball_10 = context.get('sum_ball_10')
                    sum_ball_15 = context.get('sum_ball_15')
                    sum_ball_45 = context.get('sum_ball_45')

                    pilot_dict[key]['balls_in_car'] = context.get('balls_in_car')
                    pilot_dict[key]['sum_total'] = old_sum_total + sum_ball

                    pilot_dict[key]['sum_ball_5'] = old_sum_ball_5 + sum_ball_5
                    pilot_dict[key]['sum_ball_10'] = old_sum_ball_10 + sum_ball_10
                    pilot_dict[key]['sum_ball_15'] = old_sum_ball_15 + sum_ball_15
                    pilot_dict[key]['sum_ball_45'] = old_sum_ball_45 + sum_ball_45

                else:
                    context = get_balls_in_car(
                        distribution_detail_set=dm.distributiondetail_set.all(), balls_in_car={}
                    )
                    sum_ball_5 = context.get('sum_ball_5')
                    sum_ball_10 = context.get('sum_ball_10')
                    sum_ball_15 = context.get('sum_ball_15')
                    sum_ball_45 = context.get('sum_ball_45')

                    sum_ball = context.get('sum_ball')
                    pilot_dict[key] = {
                        'pilot_id': dm.pilot.id,
                        'pilot_names': dm.pilot.names,
                        'license_plate': dm.truck.license_plate,
                        'balls_in_car': context.get('balls_in_car'),
                        'sum_total': sum_ball,
                        'sum_ball_5': sum_ball_5,
                        'sum_ball_10': sum_ball_10,
                        'sum_ball_15': sum_ball_15,
                        'sum_ball_45': sum_ball_45,
                    }
                # if sum_ball_5 > 0:  # BALON DE 10
                acm_sum_5 += sum_ball_5
                # elif sum_ball_10 > 0:  # BALON DE 15
                acm_sum_10 += sum_ball_10
                # elif sum_ball_15 > 0:  # BALON DE 5
                acm_sum_15 += sum_ball_15
                # elif sum_ball_45 > 0:  # BALON DE 45
                acm_sum_45 += sum_ball_45
                sum_total += sum_ball

        # TABLE 2

        d = get_orders_for_status_account(subsidiary_obj=subsidiary_obj)

        summary_sum_total_remaining_repay_loan = d['summary_sum_total_remaining_repay_loan']
        summary_sum_total_remaining_return_loan = d['summary_sum_total_remaining_return_loan']
        client_dict = d['client_dict']

        return render(request, 'sales/status_account.html', {
            'pilot_dict': pilot_dict,
            'sum_total': sum_total,
            'client_dict': client_dict,
            'summary_sum_total_remaining_repay_loan': '{:,}'.format(
                round(float(summary_sum_total_remaining_repay_loan), 2)),
            'summary_sum_total_remaining_return_loan': summary_sum_total_remaining_return_loan,
            'acm_sum_5': acm_sum_5,
            'acm_sum_10': acm_sum_10,
            'acm_sum_15': acm_sum_15,
            'acm_sum_45': acm_sum_45,
        })


def check_loan_payment(request):
    if request.method == 'GET':
        lps = str(request.GET.get('lps', '')).replace('[', '').replace(']', '')
        operation = bool(request.GET.get('operation', ''))
        array_lps = lps.split(", ")
        map_object = map(int, array_lps)
        list_of_integers = list(map_object)

        LoanPayment.objects.filter(id__in=list_of_integers).update(is_check=operation)

        return JsonResponse({
            'message': 'ok',
        })


def sum_quantity_by_order_detail(month=None, product_id=None):
    subsidiaries = [1, 2, 3, 4, 6]
    my_date = datetime.now()
    order_detail_set = OrderDetail.objects.filter(
        order__subsidiary__id__in=subsidiaries,
        order__create_at__month=month,
        order__create_at__year=my_date.year,
        order__type__in=['R', 'V'],
        product__id=product_id
    ).filter(~Q(unit__name='B')).annotate(
        sum=Sum('quantity_sold')
    ).aggregate(Sum('sum'))

    return order_detail_set['sum__sum']


def comparative_sales_and_purchases_report(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        my_date = datetime.now()
        month_dict = []
        subsidiaries = [1, 2, 3, 4, 6]

        float_purchases_sum_total = 0
        sum_float_req_quantity_kg = 0
        sum_float_req_amount_pen = 0
        sum_acc_total_all_balls = 0
        sum_float_sum_total_all_balls = 0
        sum_acc_total_orders = 0
        sum_total_sum_charge = 0
        sum_total_travel = 0
        sum_float_purchases_sum_total = 0

        merge_scope = None

        month_names = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SETIEMBRE', 'OCTUBRE',
                       'NOVIEMBRE', 'DICIEMBRE']

        my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='G')  # pluspetrol

        my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='I')  # tu almacen insumos

        product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')

        product_store_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_glp_obj,
                                                     product=product_obj)

        for i in range(1, 13):

            sum_5kg = sum_quantity_by_order_detail(month=i, product_id=2)
            sum_10kg = sum_quantity_by_order_detail(month=i, product_id=1)
            sum_15kg = sum_quantity_by_order_detail(month=i, product_id=12)
            sum_45kg = sum_quantity_by_order_detail(month=i, product_id=3)

            if sum_5kg is not None:
                float_sum_5kg = float(sum_5kg)
            else:
                float_sum_5kg = 0
            if sum_10kg is not None:
                float_sum_10kg = float(sum_10kg)
            else:
                float_sum_10kg = 0
            if sum_15kg is not None:
                float_sum_15kg = float(sum_15kg)
            else:
                float_sum_15kg = 0
            if sum_45kg is not None:
                float_sum_45kg = float(sum_45kg)
            else:
                float_sum_45kg = 0

            sum_total_all_balls = float_sum_10kg + (float_sum_5kg * 0.5) + (float_sum_15kg * 1.5) + (
                    float_sum_45kg * 4.5)

            order_detail_set = OrderDetail.objects.filter(
                order__subsidiary__id__in=subsidiaries,
                order__create_at__month=i,
                order__create_at__year=my_date.year,
                order__type__in=['R', 'V'],
            ).annotate(
                sum_subtotal=Sum(F('quantity_sold') * F('price_unit'))
            ).aggregate(Sum('sum_subtotal'))

            sum_total_orders = order_detail_set['sum_subtotal__sum']

            if sum_total_orders is not None:
                float_sum_total_orders = float(sum_total_orders)
            else:
                float_sum_total_orders = 0

            if sum_total_all_balls is not None:
                float_sum_total_all_balls = float(sum_total_all_balls)
            else:
                float_sum_total_all_balls = 0

            req_quantity_kg = RequirementDetail_buys.objects.filter(
                requirement_buys__approval_date__month=i,
                requirement_buys__approval_date__year=my_date.year,
                requirement_buys__status='2',
                requirement_buys__subsidiary=subsidiary_obj).aggregate(Sum('quantity'))

            sum_req_quantity_kg = req_quantity_kg['quantity__sum']

            if sum_req_quantity_kg is not None:
                float_req_quantity_kg = float(sum_req_quantity_kg)
            else:
                float_req_quantity_kg = 0

            req_amount_pen = RequirementDetail_buys.objects.filter(
                requirement_buys__approval_date__month=i,
                requirement_buys__approval_date__year=my_date.year,
                requirement_buys__status='2',
                requirement_buys__subsidiary=subsidiary_obj).aggregate(Sum('amount_pen'))

            sum_req_amount_pen = req_amount_pen['amount_pen__sum']

            if sum_req_amount_pen is not None:
                float_req_amount_pen = float(sum_req_amount_pen)
            else:
                float_req_amount_pen = 0

            # -----------------------------------------------------------------------------------------

            total_sum_charge = 0
            _total_travel = 0
            total_charge = 0

            kardex_set = Kardex.objects.filter(product_store=product_store_obj).filter(
                Q(programming_invoice__date_arrive__month=i, programming_invoice__date_arrive__year=my_date.year, ) | Q(
                    requirement_detail__requirement_buys__approval_date__month=i,
                    requirement_detail__requirement_buys__approval_date__year=my_date.year),
                programming_invoice__id__isnull=False, requirement_detail__isnull=True
            ).distinct('programming_invoice__requirementBuysProgramming', 'programming_invoice__quantity',
                       'programming_invoice__requirementBuysProgramming__number_scop', 'create_at').select_related(
                'programming_invoice'
            ).annotate(
                sum_total=Subquery(
                    Programminginvoice.objects.filter(requirementBuysProgramming_id=OuterRef(
                        'programming_invoice__requirementBuysProgramming_id')).filter(
                        subsidiary_store_origin=my_subsidiary_store_glp_obj,
                        subsidiary_store_destiny=my_subsidiary_store_insume_obj).annotate(
                        return_sum_total=Sum(F('quantity'))
                    )
                )
            ).values('programming_invoice__requirementBuysProgramming',
                     'programming_invoice__requirementBuysProgramming__number_scop',
                     'programming_invoice__quantity').order_by('create_at')

            # print(kardex_set)

            # programming_invoice_set = Programminginvoice.objects.filter(
            #     subsidiary_store_origin=my_subsidiary_store_glp_obj,
            #     subsidiary_store_destiny=my_subsidiary_store_insume_obj,
            #     kardex__product_store=product_store_obj,
            # ).filter(
            #     Q(date_arrive__month=i,) | Q(kardex__requirement_detail__requirement_buys__approval_date__month=i)
            # ).values('requirementBuysProgramming', 'requirementBuysProgramming__number_scop').annotate(totals=Sum('quantity')).order_by('kardex__create_at')
            #
            # # print(programming_invoice_set)

            # -----------------------------------------------------------------------------------------

            for pi in kardex_set:
                my_charge = 0
                other_charge = 0
                my_charge = pi['programming_invoice__quantity']
                total_charge = total_charge + my_charge
                total_sum_charge = total_sum_charge + my_charge

                if merge_scope == pi['programming_invoice__requirementBuysProgramming__number_scop']:
                    # dictionary.pop(len(dictionary) - 1)
                    # total_charge = total_charge - other_charge - my_charge
                    _total_travel = _total_travel - 1
                    # total_sum_charge = total_sum_charge - my_charge - other_charge
                _total_travel = _total_travel + 1
                merge_scope = pi['programming_invoice__requirementBuysProgramming__number_scop']

            if i >= 8 and my_date.year > 2020:
                purchase_set = Purchase.objects.filter(
                    subsidiary=subsidiary_obj, purchase_date__month=i, purchase_date__year=my_date.year,
                    status__in=['S', 'A'], type_bill='F'
                ).prefetch_related(
                    Prefetch(
                        'purchasedetail_set', queryset=PurchaseDetail.objects.select_related('unit', 'product')
                    )
                ).select_related('supplier', 'truck').annotate(
                    sum_total=Subquery(
                        PurchaseDetail.objects.filter(purchase_id=OuterRef('id')).annotate(
                            return_sum_total=Sum(F('quantity') * F('price_unit'))).values('return_sum_total')[:1]
                    )
                ).aggregate(Sum('sum_total'))

                purchases_sum_total = purchase_set['sum_total__sum']

                if purchases_sum_total is not None:
                    float_purchases_sum_total = float(purchases_sum_total)
                else:
                    float_purchases_sum_total = 0

            sum_total_all_balls2 = float_sum_total_all_balls / 0.1

            sum_float_req_quantity_kg += float_req_quantity_kg
            sum_float_req_amount_pen += float_req_amount_pen
            sum_acc_total_all_balls += sum_total_all_balls
            sum_float_sum_total_all_balls += sum_total_all_balls2
            sum_acc_total_orders += float_sum_total_orders
            sum_total_sum_charge += total_sum_charge
            sum_total_travel += _total_travel
            sum_float_purchases_sum_total += float_purchases_sum_total

            item = {
                'month': i,
                'month_names': month_names[i - 1],
                'req_quantity_kg': '{:,}'.format(round(float_req_quantity_kg), 2),
                'req_amount_pen': '{:,}'.format(round(decimal.Decimal(float_req_amount_pen), 2)),
                'sum_total_all_balls': '{:,}'.format(round(decimal.Decimal(sum_total_all_balls), 2)),
                'sum_total_all_balls2': '{:,}'.format(round(decimal.Decimal(sum_total_all_balls2), 2)),
                'sum_total_orders': '{:,}'.format(round(decimal.Decimal(float_sum_total_orders), 2)),
                'glp_kg': '{:,}'.format(round(total_sum_charge), 2),
                'glp_unit': _total_travel,
                'purchases_sum_total': '{:,}'.format(round(decimal.Decimal(float_purchases_sum_total), 2))
            }
            month_dict.append(item)

        tpl = loader.get_template('sales/comparative_sales_and purchases_grid.html')
        context = ({
            'month_dict': month_dict,
            'sum_float_req_quantity_kg': '{:,}'.format(round(sum_float_req_quantity_kg), 2),
            'sum_float_req_amount_pen': '{:,}'.format(round(decimal.Decimal(sum_float_req_amount_pen), 2)),
            'sum_acc_total_all_balls': '{:,}'.format(round(decimal.Decimal(sum_acc_total_all_balls), 2)),
            'sum_float_sum_total_all_balls': '{:,}'.format(round(decimal.Decimal(sum_float_sum_total_all_balls), 2)),
            'sum_acc_total_orders': '{:,}'.format(round(decimal.Decimal(sum_acc_total_orders), 2)),
            'sum_total_sum_charge': '{:,}'.format(round(decimal.Decimal(sum_total_sum_charge), 2)),
            'sum_total_travel': '{:,}'.format(round(sum_total_travel), 2),
            'sum_float_purchases_sum_total': '{:,}'.format(round(decimal.Decimal(sum_float_purchases_sum_total), 2)),
        })

        return render(request, 'sales/comparative_sales_and_purchases_report.html', {
            'grid': tpl.render(context, request),
        })


def purchase_report_by_category(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        return render(request, 'sales/report_purchases_by_category.html', {
            'formatdate': formatdate,
        })

    elif request.method == 'POST':

        year = str(request.POST.get('year'))

        month_names = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SETIEMBRE', 'OCTUBRE',
                       'NOVIEMBRE', 'DICIEMBRE']
        sector_set = ['N', 'L', 'P', 'PR', 'R', 'C', 'G', 'S', 'SU', 'LU', 'LA', 'M', 'PE', 'O']
        sector_choices = ['NO ESPECIFICA', 'LLANTAS', 'PINTURA', 'PRECINTO', 'REPUESTO', 'COMBUSTIBLE', 'GLP',
                          'SEGUROS', 'SUNAT', 'LUBRICANTES', 'LAVADO', 'MANTENIMIENTO', 'PEAJES', 'OTROS']

        purchase_dict = []
        sum_float_purchases_sum_total = 0
        float_purchases_sum_total = 0
        float_total_month = 0


        for i in range(1, 13):

            sum_total_month = 0
            month_item = {
                'month': i,
                'month_names': month_names[i - 1],
                'sector_list': [],
                'total_month': sum_total_month
            }

            for s in range(len(sector_set)):

                purchase_set = Purchase.objects.filter(
                    purchase_date__month=i, purchase_date__year=year, supplier__sector=sector_set[s],
                    status='A'
                ).prefetch_related(
                    Prefetch(
                        'purchasedetail_set', queryset=PurchaseDetail.objects.select_related('unit', 'product')
                    )
                ).select_related('supplier').annotate(
                    sum_total=Subquery(
                        PurchaseDetail.objects.filter(purchase_id=OuterRef('id')).annotate(
                            return_sum_total=Sum(F('quantity') * F('price_unit'))).values('return_sum_total')[:1]
                    )
                ).aggregate(Sum('sum_total'))

                purchases_sum_total = purchase_set['sum_total__sum']

                if purchases_sum_total is not None:
                    float_purchases_sum_total = float(purchases_sum_total)
                else:
                    float_purchases_sum_total = 0

                item = {
                    'sector': s,
                    'sector_name': sector_choices[s],
                    'purchases_sum_total': '{:,}'.format(round(decimal.Decimal(float_purchases_sum_total), 2))
                }
                month_item.get('sector_list').append(item)

                sum_total_month += float_purchases_sum_total
            month_item['total_month'] = '{:,}'.format(round(decimal.Decimal(sum_total_month), 2))

            purchase_dict.append(month_item)

        # print(purchase_dict)
        tpl = loader.get_template('sales/report_purchases_by_category_grid.html')
        context = ({
            'purchase_dict': purchase_dict,
            'sum_float_purchases_sum_total': sum_float_purchases_sum_total,
        })

        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def test(request):
    if request.method == 'GET':
        client_id = 'T'
        start_date = '2021-05-01'
        end_date = '2021-08-02'

        purchase_set = Purchase.objects.filter(
            subsidiary=1, purchase_date__range=[start_date, end_date],
        ).prefetch_related(
            Prefetch(
                'purchasedetail_set', queryset=PurchaseDetail.objects.select_related('unit', 'product')
            )
        ).select_related('supplier', 'truck').annotate(
            sum_total=Subquery(
                PurchaseDetail.objects.filter(purchase_id=OuterRef('id')).annotate(
                    return_sum_total=Sum(F('quantity') * F('price_unit'))).values('return_sum_total')[:1]
            )
        )

        tpl = loader.get_template('buys/report_purchases_all_grid.html')
        context = ({
            'purchase_set': purchase_set
        })

        return render(request, 'sales/test.html', {
            'grid': tpl.render(context, request),
        })
