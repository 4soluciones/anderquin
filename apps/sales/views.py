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
from apps.comercial.models import DistributionMobil, Truck, DistributionDetail, \
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
from apps.sales.views_SUNAT import send_bill_nubefact, send_receipt_nubefact, query_apis_net_dni_ruc
from apps.sales.number_to_letters import numero_a_letras, numero_a_moneda
from django.utils import timezone
from django.db.models import Min, Sum, Max, Q, F, Prefetch, Subquery, OuterRef, Value
from django.db.models.functions import Greatest
from django.db.models.functions import (
    ExtractDay, ExtractMonth, ExtractQuarter, ExtractWeek,
    ExtractWeekDay, ExtractIsoYear, ExtractYear,
)

from ..accounting.models import Bill, BillPurchase, BillDetail
from ..buys.models import PurchaseDetail, Purchase, CreditNote
from apps.sales.funtions import *


# class Home(TemplateView):
#     template_name = 'sales/home.html'


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
            print(data['form_invalid'])
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
        subsidiaries = Subsidiary.objects.all().order_by('serial')
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
                'purchase_detail',
                'order_detail__order',
                'loan_payment',
                'guide_detail__guide__guide_motive',
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
        contexto['type_client'] = Client._meta.get_field('type_client').choices
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


def client_save(request):
    if request.method == 'GET':
        client_request = request.GET.get('client', '')
        data_client = json.loads(client_request)

        client_id = str(data_client["client_id"])
        document_type = str(data_client["document_type"])
        document_number = str(data_client["document_number"])
        names = str(data_client["names"])
        phone = str(data_client["phone"])
        email = str(data_client["email"])
        type_client = str(data_client["type_client"])
        siaf = None
        if str(data_client["siaf"]) != '':
            siaf = str(data_client["siaf"])

        document_type_obj = DocumentType.objects.get(id=document_type)

        client_obj = Client(
            names=names.upper(),
            phone=phone,
            email=email,
            cod_siaf=siaf,
            type_client=type_client
        )
        client_obj.save()

        client_type_obj = ClientType(
            client=client_obj,
            document_type=document_type_obj,
            document_number=document_number
        )
        client_type_obj.save()

        if type_client == 'PU':
            public_address = str(data_client["publicAddress"])
            public_district = str(data_client["publicDistrict"])
            district_obj = District.objects.get(id=public_district)

            client_address_obj = ClientAddress(
                client=client_obj,
                address=public_address.upper(),
                district=district_obj
            )
            client_address_obj.save()

        elif type_client == 'PR':
            for d in data_client['Addresses']:
                new_address = str(d['new_address'])
                district = str(d['district'])

                district_obj = District.objects.get(id=district)

                client_address_obj = ClientAddress(
                    client=client_obj,
                    address=new_address.upper(),
                    district=district_obj
                )
                client_address_obj.save()

        return JsonResponse({
            'success': True,
            'message': 'Cliente Registrado',
        }, status=HTTPStatus.OK)
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


@csrf_exempt
def new_client(request):
    data = dict()
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
        type_client = str(request.POST.get('type_client', ''))
        client_id = int(request.POST.get('client_id', ''))  # solo se usa al editar
        if operation == 'N':
            if len(names) > 0:
                data_client = {
                    'names': names.upper(),
                    'phone': phone,
                    'email': email,
                    'type_client': type_client
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
                            'address': address.upper(),
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
            client_obj.type_client = type_client
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


class SalesOrder(View):
    template_name = 'sales/sales_list.html'

    def get_context_data(self, **kwargs):
        error = ""
        user_id = self.request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        context = {}
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        if subsidiary_obj is None:
            error = "No tiene una sede definida."
        else:
            sales_store = SubsidiaryStore.objects.filter(
                subsidiary=subsidiary_obj, category='V').first()

            document_types = DocumentType.objects.all()
            series_set = Subsidiary.objects.filter(id=subsidiary_obj.id)
            cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
            cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
            # family_set = ProductFamily.objects.all()
            users_set = User.objects.filter(is_superuser=False, is_staff=True)

            selected_choices = 'EC', 'L', 'Y'
            context['choices_account'] = cash_set
            context['choices_account_bank'] = cash_deposit_set
            context['error'] = error
            context['sales_store'] = sales_store
            context['subsidiary'] = subsidiary_obj
            # context['family_set'] = family_set
            # context['districts'] = District.objects.all()
            context['document_types'] = document_types
            context['date'] = formatdate
            context['choices_payments'] = [(k, v) for k, v in TransactionPayment._meta.get_field('type').choices
                                           if k not in selected_choices]
            context['series'] = series_set
            context['order_set'] = Order._meta.get_field('order_type').choices
            context['users'] = users_set

            return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


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
            price_purchase = request.POST.get('price_purchase', '')
            price_sale = request.POST.get('price_sale', '')
            id_unit = request.POST.get('unit', '')
            quantity_minimum = request.POST.get('quantity_minimum', '')

            if decimal.Decimal(price_sale) == 0 or decimal.Decimal(quantity_minimum) == 0 or decimal.Decimal(
                    price_purchase) == 0:
                data['error'] = "Ingrese valores validos."
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

            product_obj = Product.objects.get(id=int(id_product))
            unit_obj = Unit.objects.get(id=int(id_unit))

            try:
                product_detail_obj = ProductDetail(
                    product=product_obj,
                    price_purchase=decimal.Decimal(price_purchase),
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
        price_purchase = request.POST.get('price_purchase', '')
        price_sale = request.POST.get('price_sale', '')
        id_unit = request.POST.get('unit', '')
        quantity_minimum = request.POST.get('quantity_minimum', '')

        if decimal.Decimal(price_sale) == 0 or decimal.Decimal(quantity_minimum) == 0 or decimal.Decimal(
                price_purchase) == 0:
            data['error'] = "Ingrese valores validos."
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        product_obj = Product.objects.get(id=int(id_product))
        unit_obj = Unit.objects.get(id=int(id_unit))

        product_detail_obj = ProductDetail.objects.get(id=int(id_product_detail))
        product_detail_obj.quantity_minimum = quantity_minimum
        product_detail_obj.price_sale = price_sale
        product_detail_obj.price_purchase = price_purchase
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


@csrf_exempt
def save_order(request):
    if request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        _client_id = request.POST.get('client-id', '')
        _type_payment = request.POST.get('transaction_payment_type', '')
        _serial = request.POST.get('serial', '')
        _date = request.POST.get('date', '')
        _sum_total = request.POST.get('sum-total', '')

        subsidiary_store_sales_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
        client_obj = Client.objects.get(pk=int(_client_id))

        order_obj = Order(
            order_type='V',
            client=client_obj,
            serial=_serial,
            user=user_obj,
            total=decimal.Decimal(_sum_total),
            status='C',
            subsidiary_store=subsidiary_store_sales_obj,
            subsidiary=subsidiary_obj,
            create_at=_date,
            correlative=get_correlative_order(subsidiary_obj, 'V'),
            way_to_pay_type=_type_payment
        )
        order_obj.save()

        detail = json.loads(request.POST.get('detail', ''))

        for detail in detail:
            product_id = int(detail['product'])
            unit_id = int(detail['unit'])
            quantity = decimal.Decimal(detail['quantity'])
            price = decimal.Decimal(detail['price'])
            total = decimal.Decimal(detail['detailTotal'])
            store_product_id = int(detail['store'])

            product_obj = Product.objects.get(id=product_id)
            unit_obj = Unit.objects.get(id=unit_id)
            product_store_obj = ProductStore.objects.get(id=store_product_id)
            quantity_minimum_unit = calculate_minimum_unit(quantity, unit_obj, product_obj)

            order_detail_obj = OrderDetail(
                order=order_obj,
                product=product_obj,
                quantity_sold=quantity,
                price_unit=price,
                unit=unit_obj,
                status='V'
            )
            order_detail_obj.save()

            kardex_ouput(product_store_obj.id, quantity_minimum_unit, order_detail_obj=order_detail_obj)

            code_operation = '-'

            cash_obj = None
            if _type_payment == 'E':
                cash_casing_id = request.POST.get('cash_id', '')
                date_cash_casing = request.POST.get('date_cash', '')
                cash_obj = Cash.objects.get(id=int(cash_casing_id))
            elif _type_payment == 'D':
                cash_deposit_id = request.POST.get('id_cash_deposit', '')
                cash_obj = Cash.objects.get(id=int(cash_deposit_id))
                date = request.POST.get('date', '')
                code_operation = request.POST.get('code-operation', '')

            if _type_payment == 'E' or _type_payment == 'D':
                loan_payment_obj = LoanPayment(
                    pay=decimal.Decimal(_sum_total),
                    order_detail=order_detail_obj,
                    create_at=_date,
                    type='V',
                    operation_date=_date
                )
                loan_payment_obj.save()

                transaction_payment_obj = TransactionPayment(
                    payment=decimal.Decimal(_sum_total),
                    type=_type_payment,
                    order=order_obj,
                    operation_code=code_operation,
                    loan_payment=loan_payment_obj
                )
                transaction_payment_obj.save()

                cash_flow_obj = CashFlow(
                    transaction_date=_date,
                    description='VENTA: ' + str(order_obj.subsidiary.serial) + '-' + str(
                        order_obj.correlative).zfill(6),
                    document_type_attached='T',
                    type=_type_payment,
                    total=_sum_total,
                    operation_code=code_operation,
                    order=order_obj,
                    user=user_obj,
                    cash=cash_obj
                )
                cash_flow_obj.save()

        # if _type == 'E':
        #     if _bill_type == 'F':
        #         r = send_bill_nubefact(order_sale_obj.id)
        #         msg_sunat = r.get('sunat_description')
        #         sunat_pdf = r.get('enlace_del_pdf')
        #         codigo_hash = r.get('codigo_hash')
        #         if codigo_hash:
        #             order_bill_obj = OrderBill(order=order_sale_obj,
        #                                        serial=r.get('serie'),
        #                                        type=r.get('tipo_de_comprobante'),
        #                                        sunat_status=r.get('aceptada_por_sunat'),
        #                                        sunat_description=r.get('sunat_description'),
        #                                        user=user_obj,
        #                                        sunat_enlace_pdf=r.get('enlace_del_pdf'),
        #                                        code_qr=r.get('cadena_para_codigo_qr'),
        #                                        code_hash=r.get('codigo_hash'),
        #                                        n_receipt=r.get('numero'),
        #                                        status='E',
        #                                        created_at=order_sale_obj.create_at,
        #                                        is_demo=value_is_demo
        #                                        )
        #             order_bill_obj.save()
        #         else:
        #             objects_to_delete = OrderDetail.objects.filter(order=order_sale_obj)
        #             objects_to_delete.delete()
        #             order_sale_obj.delete()
        #             if r.get('errors'):
        #                 data = {'error': str(r.get('errors'))}
        #             elif r.get('error'):
        #                 data = {'error': str(r.get('error'))}
        #             response = JsonResponse(data)
        #             response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        #             return response
        #
        #     elif _bill_type == 'B':
        #         r = send_receipt_nubefact(order_sale_obj.id, is_demo)
        #         msg_sunat = r.get('sunat_description')
        #         sunat_pdf = r.get('enlace_del_pdf')
        #         codigo_hash = r.get('codigo_hash')
        #         if codigo_hash:
        #             order_bill_obj = OrderBill(order=order_sale_obj,
        #                                        serial=r.get('serie'),
        #                                        type=r.get('tipo_de_comprobante'),
        #                                        sunat_status=r.get('aceptada_por_sunat'),
        #                                        sunat_description=r.get('sunat_description'),
        #                                        user=user_obj,
        #                                        sunat_enlace_pdf=r.get('enlace_del_pdf'),
        #                                        code_qr=r.get('cadena_para_codigo_qr'),
        #                                        code_hash=r.get('codigo_hash'),
        #                                        n_receipt=r.get('numero'),
        #                                        status='E',
        #                                        created_at=order_sale_obj.create_at,
        #                                        is_demo=value_is_demo
        #                                        )
        #             order_bill_obj.save()
        #         else:
        #             objects_to_delete = OrderDetail.objects.filter(order=order_sale_obj)
        #             objects_to_delete.delete()
        #             order_sale_obj.delete()
        #             if r.get('errors'):
        #                 data = {'error': str(r.get('errors'))}
        #             elif r.get('error'):
        #                 data = {'error': str(r.get('error'))}
        #             response = JsonResponse(data)
        #             response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        #             return response

        return JsonResponse({
            'message': 'Venta generada',
            # 'msg_sunat': msg_sunat,
            # 'sunat_pdf': sunat_pdf,
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


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
        guide_detail_obj=None,
        distribution_detail_obj=None,
        order_detail_obj=None,
        loan_payment_obj=None,
        bill_detail_obj=None
):
    new_kardex = {
        'operation': 'C',
        'quantity': 0,
        'price_unit': 0,
        'price_total': 0,
        'remaining_quantity': decimal.Decimal(stock),
        'remaining_price': decimal.Decimal(price_unit),
        'remaining_price_total': decimal.Decimal(stock) * decimal.Decimal(price_unit),
        'distribution_detail': distribution_detail_obj,
        'guide_detail': guide_detail_obj,
        'order_detail': order_detail_obj,
        'product_store': product_store_obj,
        'purchase_detail': purchase_detail_obj,
        'loan_payment': loan_payment_obj,
        'bill_detail': bill_detail_obj,
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()


def kardex_input(
        product_store_id,
        quantity_purchased,
        price_unit,
        purchase_detail_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        order_detail_obj=None,
        loan_payment_obj=None,
        bill_detail_obj=None
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
        'distribution_detail': distribution_detail_obj,
        'guide_detail': guide_detail_obj,
        'order_detail': order_detail_obj,
        'product_store': product_store,
        'purchase_detail': purchase_detail_obj,
        'loan_payment': loan_payment_obj,
        'bill_detail': bill_detail_obj,
    }
    kardex = Kardex.objects.create(**new_kardex)
    kardex.save()

    product_store.stock = new_stock
    product_store.save()


def kardex_ouput(
        product_store_id,
        quantity_sold,
        order_detail_obj=None,
        guide_detail_obj=None,
        distribution_detail_obj=None,
        loan_payment_obj=None,
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
        'distribution_detail': distribution_detail_obj,
        'guide_detail': guide_detail_obj,
        'order_detail': order_detail_obj,
        'product_store': product_store,
        'loan_payment': loan_payment_obj,
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


def order_list(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")
        client_set = Client.objects.all().values('id', 'names')

        return render(request, 'sales/account_status_list.html', {
            'client_set': client_set,
            'formatdate': formatdate,
        })


def get_dict_orders(client_obj=None, start_date=None, end_date=None):
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
            cash_flow_set = o.cashflow_set.all()
            new = {
                'id': o.id,
                'type': o.get_type_display(),
                'client': o.client.names,
                'user': o.user.username,
                'date': o.create_at,
                'order_detail_set': [],
                'status': o.get_status_display(),
                'total': o.total,
                'subtotal': 0,
                'total_repay_loan': '{:,}'.format(
                    total_remaining_repay_loan(order_detail_set=order_detail_set).quantize(decimal.Decimal('0.00'),
                                                                                           rounding=decimal.ROUND_HALF_EVEN)),
                'total_remaining_repay_loan': '{:,}'.format(
                    total_remaining_repay_loan(order_detail_set=order_detail_set).quantize(decimal.Decimal('0.00'),
                                                                                           rounding=decimal.ROUND_HALF_EVEN)),
                'total_spending': '{:,}'.format(
                    total_cash_flow_spending(cashflow_set=cash_flow_set).quantize(decimal.Decimal('0.00'),
                                                                                  rounding=decimal.ROUND_HALF_EVEN)),
                'details_count': order_detail_set.count(),
                'rowspan': 0,
                'is_review': o.is_review,
                'has_loans': False
            }
            subtotal = 0

            for d in order_detail_set:
                _type = '-'
                loan_payment_set = []
                for lp in d.loanpayment_set.all():
                    _payment_type = '-'
                    _cash_flow = None
                    transaction_payment_set = lp.transactionpayment_set.all()
                    if transaction_payment_set.exists():
                        transaction_payment = None
                        for t in transaction_payment_set:
                            transaction_payment = t
                        _cash_flow = get_cash_flow(order=o, transactionpayment=transaction_payment)
                        _payment_type = transaction_payment.get_type_display()

                    loan_payment = {
                        'id': lp.id,
                        'quantity': lp.quantity,
                        'date': lp.create_at,
                        'operation_date': lp.operation_date,
                        'price': '{:,}'.format(
                            lp.price.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)),
                        'type': _payment_type,
                        'cash_flow': _cash_flow,
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
                    'price_unit': str(round(d.price_unit, 6)),
                    'multiply': d.multiply,
                    'repay_loan': '{:,}'.format(round(repay_loan(loan_payment_set=d.loanpayment_set.all())), 2),
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
            new['subtotal'] = round(subtotal, 2)
            dictionary.append(new)

    sum_total = 0
    sum_total_repay_loan = 0
    sum_total_remaining_repay_loan = 0
    sum_total_cash_flow_spending = 0
    difference_debt = 0

    if order_set.exists():
        sum_quantity_total = 0
        for o in order_set:
            order_detail_set = o.orderdetail_set.all()
            cash_flow_set = o.cashflow_set.all()
            sum_total_repay_loan += total_repay_loan(order_detail_set=order_detail_set)
            sum_total_remaining_repay_loan += total_remaining_repay_loan(order_detail_set=order_detail_set)
            sum_total_cash_flow_spending += total_cash_flow_spending(cashflow_set=cash_flow_set)
            total_quantity_set = order_detail_set.values('quantity_sold').annotate(
                totals_quantity=Sum('quantity_sold')).aggregate(Sum('totals_quantity'))

            sum_quantity_total += total_quantity_set['totals_quantity__sum']
            difference_debt = sum_total_remaining_repay_loan - sum_total_repay_loan

        total_set = order_set.values('client').annotate(totals=Sum('total'))
        sum_total = total_set[0].get('totals')

    tpl = loader.get_template('sales/account_order_list.html')
    context = ({
        'dictionary': dictionary,
        'sum_total': '{:,}'.format(round(float(sum_total), 2)),
        'sum_total_repay_loan': '{:,}'.format(round(float(sum_total_repay_loan), 2)),
        'sum_total_remaining_repay_loan': '{:,}'.format(round(float(sum_total_remaining_repay_loan), 2)),
        'sum_total_cash_flow_spending': '{:,}'.format(round(float(sum_total_cash_flow_spending), 2)),
        'sum_quantity_total': sum_quantity_total,
        'difference_debt': '{:,}'.format(round(float(difference_debt), 2)),
        'client_obj': client_obj,
    })

    return tpl.render(context)


def get_orders_by_client(request):
    if request.method == 'GET':
        client_id = request.GET.get('client_id', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        client_obj = Client.objects.get(pk=int(client_id))
        return JsonResponse({
            'grid': get_dict_orders(client_obj=client_obj, start_date=start_date, end_date=end_date),
        }, status=HTTPStatus.OK)


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
        transaction_account_obj = TransactionAccount.objects.all()
        user_id = request.user.id
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        tpl = loader.get_template('sales/new_expense.html')
        cash_set = Cash.objects.filter(accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        context = ({
            'choices_document': TransactionAccount._meta.get_field('document_type_attached').choices,
            'transactionaccount': transaction_account_obj,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'date': formatdate,
            'start_date': start_date,
            'end_date': end_date,
            'user': user_obj
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
            'grid': get_dict_orders(client_obj=order_obj.client, start_date=start_date, end_date=end_date)
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

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'grid': get_dict_orders(client_obj=detail_obj.order.client, start_date=start_date,
                                    end_date=end_date),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


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


def get_price_of_product(product_detail_set=None, product=None, unit=None):
    price = 0
    for pd in product_detail_set:
        if pd.product == product and pd.unit == unit:
            price = pd.price_sale
    return price


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


def quotation_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    worker_obj = Worker.objects.filter(user=user_obj).last()
    employee = Employee.objects.get(worker=worker_obj)
    document_types = DocumentType.objects.all()
    mydate = datetime.now()
    formatdate = mydate.strftime("%Y-%m-%d")
    series_set = Subsidiary.objects.filter(id=subsidiary_obj.id)
    cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
    cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
    sales_store = SubsidiaryStore.objects.filter(
        subsidiary=subsidiary_obj, category='V').first()
    users_set = User.objects.all()

    return render(request, 'sales/quotation_list.html', {
        'choices_account': cash_set,
        'choices_account_bank': cash_deposit_set,
        'employee': employee,
        'sales_store': sales_store,
        'subsidiary': subsidiary_obj,
        'document_types': document_types,
        'date': formatdate,
        'choices_payments': TransactionPayment._meta.get_field('type').choices,
        'series': series_set,
        'users': users_set
    })


def get_product_quotation(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        sales_store = SubsidiaryStore.objects.filter(
            subsidiary=subsidiary_obj, category='V').first()
        last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]
        product_set = None

        value = request.GET.get('value', '')
        barcode = request.GET.get('barcode', '')

        if value != '' and barcode == '':
            array_value = value.split()
            product_query = Product.objects
            full_query = None

            product_brand_set = ProductBrand.objects.filter(name__icontains=value.upper())

            for i in range(0, len(array_value)):
                q = Q(name__icontains=array_value[i]) | Q(product_brand__name__icontains=array_value[i])
                if full_query is None:
                    full_query = q
                else:
                    full_query = full_query & q

            product_set = product_query.filter(full_query).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set', queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                        .annotate(
                        last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        if value == '' and barcode != '':
            product_set = Product.objects.filter(barcode=barcode).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set', queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                        .annotate(
                        last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        t = loader.get_template('sales/quotation_product_grid.html')
        c = ({
            'subsidiary': subsidiary_obj,
            'product_dic': product_set
        })
        return JsonResponse({
            'grid': t.render(c, request),
        })


def save_quotation(request):
    if request.method == 'GET':
        quotation_request = request.GET.get('quotations', '')
        data_quotation = json.loads(quotation_request)
        type_payment = (data_quotation["type_payment"])
        has_quotation_order = ''

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))

        _date = str(data_quotation["Date"])
        client_address = str(data_quotation["Address"])
        client_id = str(data_quotation["Client"])
        client_obj = Client.objects.get(pk=int(client_id))
        client_address_set = ClientAddress.objects.filter(client=client_obj)
        if client_address_set.exists():
            client_address_obj = client_address_set.last()
            client_address_obj.address = client_address
            client_address_obj.save()
        else:
            client_address_obj = ClientAddress(
                client=client_obj,
                address=client_address
            )
            client_address_obj.save()

        sale_total = decimal.Decimal(data_quotation["SaleTotal"])
        # user_id = request.user.id
        # user_obj = User.objects.get(id=user_id)
        user_id = request.user.id
        user_subsidiary_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_subsidiary_obj)

        # user = int(data_quotation["userID"])
        # user_obj = User.objects.get(id=user)

        subsidiary_store_sales_obj = SubsidiaryStore.objects.get(
            subsidiary=subsidiary_obj, category='V')
        _bill_type = str(data_quotation["BillType"])

        validity_date = (data_quotation["validity_date"])
        date_completion = (data_quotation["date_completion"])
        place_delivery = (data_quotation["place_delivery"])
        observation = (data_quotation["observation"])

        order_sale_quotation = None
        order_sale_quotation_obj = None

        order_obj = Order(
            type='T',
            client=client_obj,
            user=user_obj,
            total=sale_total,
            subsidiary_store=subsidiary_store_sales_obj,
            create_at=_date,
            correlative=get_correlative_order(subsidiary_obj, 'T'),
            subsidiary=subsidiary_obj,
            validity_date=validity_date,
            date_completion=date_completion,
            place_delivery=place_delivery,
            observation=observation,
            way_to_pay_type=type_payment,
            has_quotation_order='S',
            order_sale_quotation=order_sale_quotation,
        )
        order_obj.save()

        for detail in data_quotation['Details']:
            quantity = decimal.Decimal(detail['Quantity'])
            price = decimal.Decimal(detail['Price'])
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)
            commentary = str(detail['_commentary'])

            order_detail_obj = OrderDetail(
                order=order_obj,
                product=product_obj,
                quantity_sold=quantity,
                price_unit=price,
                unit=unit_obj,
                commentary=commentary,
                status='V',
            )
            order_detail_obj.save()

        return JsonResponse({
            'id_sales': order_obj.id,
            'message': 'Cotización generada',
        }, status=HTTPStatus.OK)


def get_correlative_order(subsidiary_obj=None, _type=None):
    correlative = Order.objects.filter(subsidiary=subsidiary_obj, order_type=_type).aggregate(
        r=Coalesce(Max('correlative'), 0))
    return str(correlative['r'] + 1)


def modal_client_create(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")

        t = loader.get_template('sales/client_form.html')
        c = ({
            'date_now': date_now,
            'districts': District.objects.all(),
            'document_types': DocumentType.objects.all(),
            'subsidiaries': Subsidiary.objects.all(),
            'type_client': Client._meta.get_field('type_client').choices
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def modal_client_update(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        client_obj = None
        if pk:
            client_obj = Client.objects.get(id=int(pk))
        t = loader.get_template('sales/client_update.html')

        districts_dict = [
            {'id': '1702', 'description': 'PUNO'}, {'id': '1720', 'description': 'JULIACA'},
            {'id': '338', 'description': 'AREQUIPA'}, {
                'id': '1829', 'description': 'TACNA'}, {'id': '752', 'description': 'CUSCO'}, ]

        c = ({
            'client_obj': client_obj,
            # 'districts': District.objects.all(),
            'districts': districts_dict,
            'type_client': Client._meta.get_field('type_client').choices,
            'document_types': DocumentType.objects.all(),
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def client_update(request):
    if request.method == 'GET':
        client_request = request.GET.get('client', '')
        data_client = json.loads(client_request)
        client_id = data_client["client_id"]
        if client_id:

            client_obj = Client.objects.get(id=int(client_id))
            document_type = str(data_client["document_type"])
            document_number = str(data_client["document_number"])
            names = str(data_client["names"])
            phone = str(data_client["phone"])
            email = str(data_client["email"])
            type_client = str(data_client["type_client"])
            siaf = None
            if str(data_client["siaf"]) != '' and str(data_client["siaf"]) != '-':
                siaf = str(data_client["siaf"])

            document_type_obj = DocumentType.objects.get(id=document_type)

            client_obj.names = names.upper()
            client_obj.phone = phone
            client_obj.email = email
            client_obj.cod_siaf = siaf
            client_obj.type_client = type_client
            client_obj.save()

            client_type_obj = ClientType.objects.get(client=client_obj)
            client_type_obj.document_type = document_type_obj
            client_type_obj.document_number = document_number
            client_type_obj.save()

            client_to_delete = ClientAddress.objects.filter(client=client_obj)
            client_to_delete.delete()

            if type_client == 'PU':
                public_address = str(data_client["publicAddress"])
                public_district = str(data_client["publicDistrict"])
                district_obj = District.objects.get(id=public_district)

                client_address_obj = ClientAddress(
                    client=client_obj,
                    address=public_address.upper(),
                    district=district_obj
                )
                client_address_obj.save()

            elif type_client == 'PR':
                for d in data_client['Addresses']:
                    new_address = str(d['new_address'])
                    district = str(d['district'])

                    district_obj = District.objects.get(id=district)

                    client_address_obj = ClientAddress(
                        client=client_obj,
                        address=new_address.upper(),
                        district=district_obj
                    )
                    client_address_obj.save()

            return JsonResponse({
                'success': True,
                'message': 'Cliente Actualizado',
            }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'success': False,
                'message': 'No se encontro cliente, intente de nuevo',
            }, status=HTTPStatus.OK)

    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_api_client(request):
    if request.method == 'GET':
        document_number = request.GET.get('nro_document')
        type_document = str(request.GET.get('type'))
        result = ''
        address = '-'
        client_obj = None

        client_set_search = Client.objects.filter(clienttype__document_type=type_document,
                                                  clienttype__document_number=document_number)
        if client_set_search.exists():
            names = client_set_search.last().names
            data = {
                'error': 'EL ClIENTE: ' + str(names) + ' YA SE ENCUENTRA REGISTRADO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        else:
            if type_document == '01':
                type_name = 'DNI'
                r = query_apis_net_dni_ruc(document_number, type_name)
                name = r.get('nombres')
                paternal_name = r.get('apellidoPaterno')
                maternal_name = r.get('apellidoMaterno')
                if paternal_name is not None and len(paternal_name) > 0:

                    result = name + ' ' + paternal_name + ' ' + maternal_name

                    # if len(result.strip()) != 0:
                    #     client_obj = Client(
                    #         names=result.upper(),
                    #     )
                    #     client_obj.save()
                    #
                    #     document_type_obj = DocumentType.objects.get(id=type_document)
                    #
                    #     client_type_obj = ClientType(
                    #         document_type=document_type_obj,
                    #         document_number=document_number,
                    #         client=client_obj
                    #     )
                    #     client_type_obj.save()

                    # else:
                    #     data = {'error': 'NO EXISTE DNI. REGISTRE MANUALMENTE'}
                    #     response = JsonResponse(data)
                    #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    #     return response
                else:
                    data = {
                        'error': 'PROBLEMAS CON LA CONSULTA A LA RENIEC, FAVOR DE INTENTAR MAS TARDE O REGISTRE '
                                 'MANUALMENTE'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

            elif type_document == '06':
                type_name = 'RUC'
                r = query_apis_net_dni_ruc(document_number, type_name)

                if r.get('numeroDocumento') == document_number:

                    business_name = r.get('nombre')
                    address_business = r.get('direccion')
                    district = r.get('distrito')
                    province = r.get('provincia')
                    dep_city = r.get('departamento')
                    result = business_name
                    address = address_business + ' - ' + district + ' - ' + province + ' - ' + dep_city

                    # client_obj = Client(
                    #     names=result.upper(),
                    # )
                    # client_obj.save()
                    #
                    # document_type_obj = DocumentType.objects.get(id=type_document)
                    #
                    # client_type_obj = ClientType(
                    #     document_type=document_type_obj,
                    #     document_number=document_number,
                    #     client=client_obj
                    # )
                    # client_type_obj.save()

                else:
                    data = {'error': 'NO EXISTE RUC. REGISTRE MANUAL O CORREGIRLO'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

        return JsonResponse({
            # 'pk': client_obj.id,
            'result': result,
            'address': address},
            status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_clients_by_criteria(request):
    if request.method == 'GET':
        client_list = []
        value = request.GET.get('value', '').strip()
        client_type_set = ClientType.objects.select_related('client').filter(client__names__icontains=value.upper())
        client_dict = {}
        address = ''
        for ct in client_type_set:

            document_type_obj = DocumentType.objects.get(id=ct.document_type_id)

            if ct.client.clientaddress_set.last() is not None:
                address = ct.client.clientaddress_set.last().address

            client_dict = {
                'client_id': ct.client.id,
                'client_names': ct.client.names,
                'client_document_number': ct.document_number,
                'client_address': address,
                'client_type_document': ct.document_type_id,
                'client_type': document_type_obj.short_description,
                'client_siaf': ct.client.cod_siaf
            }
            client_list.append(client_dict)

        return JsonResponse({
            'client_list': client_list,
            'client_count': len(client_dict),
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_sales_quotation_by_subsidiary(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/order_quotation_list.html', {'formatdate': formatdate, })
    elif request.method == 'POST':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        if subsidiary_obj is not None:
            orders = Order.objects.filter(subsidiary=subsidiary_obj, type='T').exclude(status='A')
            start_date = str(request.POST.get('start-date'))
            end_date = str(request.POST.get('end-date'))

            if start_date == end_date:
                orders = orders.filter(create_at__date=start_date)
            else:
                orders = orders.filter(create_at__date__range=[start_date, end_date])
            if orders:
                return JsonResponse({
                    'grid': get_dict_order_quotation(orders),
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


def get_dict_order_quotation(order_set):
    dictionary = []
    sum_orders = 0

    for o in order_set:
        _order_detail = o.orderdetail_set.all()
        order_sale_quotation = ''

        if o.order_sale_quotation is not None:
            order_sale_quotation = o.order_sale_quotation.id

        order = {
            'id': o.id,
            'status': o.get_status_display(),
            'client': o.client,
            'client_nro': o.client.clienttype_set.first().document_number,
            'user': o.user,
            'total': o.total,
            'subsidiary': o.subsidiary.name,
            'create_at': o.create_at,
            'serial': o.subsidiary.serial,
            'correlative_sale': o.correlative,
            'validity_date': o.validity_date,
            'date_completion': o.date_completion,
            'place_delivery': o.place_delivery,
            # 'type_quotation': o.get_type_quotation_display(),
            # 'type_name_quotation': o.type_name_quotation,
            'observation': o.observation,
            'way_to_pay_type': o.get_way_to_pay_type_display(),
            'order_sale_quotation': order_sale_quotation,
            'type': o.get_type_display(),
            'has_quotation_order': o.has_quotation_order,
            'order_detail_set': [],
            'details': _order_detail.count()
        }
        sum_orders = sum_orders + o.total

        for d in _order_detail:
            order_detail = {
                'id': d.id,
                'product': d.product.name,
                'unit': d.unit.name,
                'quantity_sold': d.quantity_sold,
                'price_unit': d.price_unit,
                'multiply': d.multiply
            }
            order.get('order_detail_set').append(order_detail)

        dictionary.append(order)

    tpl = loader.get_template('sales/order_quotation_grid_list.html')
    context = ({
        'dictionary': dictionary,
        'sum_orders': sum_orders,
    })
    return tpl.render(context)


def get_product_grid(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        sales_store = SubsidiaryStore.objects.filter(
            subsidiary=subsidiary_obj, category='V').first()
        last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]
        product_set = None

        value = request.GET.get('value', '')
        barcode = request.GET.get('barcode', '')

        if value != '' and barcode == '':
            array_value = value.split()
            product_query = Product.objects
            full_query = None

            product_brand_set = ProductBrand.objects.filter(name__icontains=value.upper())

            for i in range(0, len(array_value)):
                q = Q(name__icontains=array_value[i]) | Q(product_brand__name__icontains=array_value[i])
                if full_query is None:
                    full_query = q
                else:
                    full_query = full_query & q

            product_set = product_query.filter(full_query).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary').exclude(
                        subsidiary_store__subsidiary=3)
                        .annotate(
                        last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        if value == '' and barcode != '':
            product_set = Product.objects.filter(barcode=barcode).select_related(
                'product_family', 'product_brand').prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary').exclude(
                        subsidiary_store__subsidiary=3)
                        .annotate(
                        last_remaining_quantity=Subquery(last_kardex.values('remaining_quantity'))
                    )
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        t = loader.get_template('sales/sales_product_grid.html')
        c = ({
            'subsidiary': subsidiary_obj,
            'product_dic': product_set
        })
        return JsonResponse({
            'grid': t.render(c, request),
        })


def check_stock(request):
    if request.method == 'GET':
        flag = True
        quantity = decimal.Decimal(request.GET.get('quantity', ''))
        product_id = int(request.GET.get('product', ''))

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        product_store_obj = ProductStore.objects.get(product__id=product_id,
                                                     subsidiary_store__subsidiary=subsidiary_obj)
        stock = product_store_obj.stock
        if decimal.Decimal(quantity) > stock:
            flag = False
        return JsonResponse({
            # 'message': 'ff',
            'flag': flag
        }, status=HTTPStatus.OK)


def utc_to_local(utc_dt):
    local_tz = pytz.timezone('America/Bogota')
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt)


def create_warehouse_sale(request):
    order_obj = None
    if request.method == 'GET':
        product_id = request.GET.get('product_id', '')
        unit_principal = request.GET.get('unit_principal', '')
        quantity_principal = request.GET.get('input_principal_val', '')
        unit_id = request.GET.get('unit_id', '')
        quantity_unit = request.GET.get('input_units', '')

        create_date = utc_to_local(datetime.now())
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        order_obj = Order(
            order_type='V',
            status='P',
            sale_type='VA',
            correlative=get_correlative_order(subsidiary_obj, 'V'),
            subsidiary=subsidiary_obj,
            create_at=create_date,
            user=user_obj
        )
        order_obj.save()

        product_obj = Product.objects.get(id=int(product_id))
        product_detail = ProductDetail.objects.filter(product=product_obj)
        if unit_principal and quantity_principal != '0' and quantity_principal != '':
            unit_obj = Unit.objects.get(id=int(unit_principal))
            product_detail_unit_principal = product_detail.filter(unit=unit_obj).last()
            detail_principal = OrderDetail(
                order=order_obj,
                product=product_obj,
                quantity_sold=quantity_principal,
                unit=unit_obj,
                price_unit=product_detail_unit_principal.price_sale,
                status='P'
            )
            detail_principal.save()
        if unit_id and quantity_unit != '0' and quantity_unit != '':
            unit_obj = Unit.objects.get(id=int(unit_id))
            product_detail_unit_principal = product_detail.filter(unit=unit_obj).last()
            detail_principal = OrderDetail(
                order=order_obj,
                product=product_obj,
                quantity_sold=quantity_unit,
                unit=unit_obj,
                price_unit=product_detail_unit_principal.price_sale,
                status='P'
            )
            detail_principal.save()

    return JsonResponse({
        'order_id': order_obj.id,
        'correlative': order_obj.correlative,
        'message': 'Codigo de Venta Generado',
    }, status=HTTPStatus.OK)


def delete_warehouse_sale(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id', '')
        order_sale_obj = Order.objects.get(id=int(order_id))
        objects_to_delete = OrderDetail.objects.filter(order=order_sale_obj)
        objects_to_delete.delete()
        order_sale_obj.delete()

    return JsonResponse({
        'message': 'Orden Eliminada',
    }, status=HTTPStatus.OK)


def get_order_by_correlative(request):
    if request.method == 'GET':
        correlative = request.GET.get('correlative', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        order_set = Order.objects.filter(subsidiary=subsidiary_obj, correlative=int(correlative), sale_type='VA')
        if order_set.exists():
            order_obj = order_set.first()
            # type_document = order_obj.client.clienttype_set.last().document_type.id
            # document_number = order_obj.client.clienttype_set.last().document_number
            # client_name = order_obj.client.names
            # validity_date = order_obj.validity_date
            # date_completion = order_obj.date_completion
            # place_delivery = order_obj.place_delivery
            # type_quotation = order_obj.type_quotation
            # type_name_quotation = order_obj.type_name_quotation
            transaction_payment_type = order_obj.way_to_pay_type
            # observation = order_obj.observation
            correlative = order_obj.correlative
            order_detail_set = OrderDetail.objects.filter(order=order_obj)
            detail = []
            for d in order_detail_set:
                quantity_minimum_unit = calculate_minimum_unit(d.quantity_sold, d.unit, d.product)
                # stock = 0
                # product_store_id = None
                # product_store_set = ProductStore.objects.filter(product=d.product,
                #                                                 subsidiary_store=d.order.subsidiary_store)

                # if product_store_set.exists():
                #     product_store_obj = product_store_set.last()
                #     product_store_id = product_store_obj.id
                #     stock = product_store_obj.stock

                new_row = {
                    'id': d.id,
                    'product_id': d.product.id,
                    'product_name': d.product.name,
                    'product_brand': d.product.product_brand.name,
                    'unit_id': d.unit.id,
                    'unit_name': d.unit.name,
                    'quantity': d.quantity_sold,
                    'price': d.price_unit,
                    # 'store': product_store_id,
                    # 'stock': round(stock, 0),
                    'unit_min': quantity_minimum_unit,
                }
                detail.append(new_row)
            return JsonResponse({
                'success': True,
                'order_id': order_obj.id,
                # 'document_type': type_document,
                # 'document_number': document_number,
                # 'client_name': client_name,
                # 'validity_date': validity_date,
                # 'date_completion': date_completion,
                # 'place_delivery': place_delivery,
                # 'type_quotation': type_quotation,
                # 'type_name_quotation': type_name_quotation,
                # 'observation': observation,
                'transaction_payment_type': transaction_payment_type,
                'correlative': correlative,
                'detail': detail,
            }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'success': False,
                'message': 'No se encontro la Cotización Numero: ' + str(correlative),
            }, status=HTTPStatus.OK)


def get_name_business(request):
    if request.method == 'GET':
        nro_document = request.GET.get('nro_document', '')
        type_document = request.GET.get('type', '')
        result = ''
        address = ''
        client_obj_search = Client.objects.filter(clienttype__document_number=nro_document)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        client_obj = None
        if client_obj_search:
            if type_document == '01' or type_document == '00':
                names = client_obj_search.first().names
                client_id = client_obj_search.first().id
                try:
                    address_search = ClientAddress.objects.filter(client_id=client_id).last()
                except ClientAddress.DoesNotExist:
                    address_search = None
                if address_search is None:
                    _address = '-'
                else:
                    _address = address_search.address

                return JsonResponse({'client_id': client_id, 'result': names, 'address': _address},
                                    status=HTTPStatus.OK)

            elif type_document == '06':
                client_id = client_obj_search.first().id
                _address__ = '-'
                try:
                    address_search = ClientAddress.objects.filter(client_id=client_id).last()
                except ClientAddress.DoesNotExist:
                    address_search = None
                if address_search is None:
                    _address__ = '-'
                else:
                    _address__ = address_search.address
                names = client_obj_search.first().names

                return JsonResponse({'client_id': client_id, 'result': names, 'address': _address__},
                                    status=HTTPStatus.OK)
        else:
            if type_document == '01':
                type_name = 'DNI'

                r = query_apis_net_dni_ruc(nro_document, type_name)
                name = r.get('nombres')
                paternal_name = r.get('apellidoPaterno')
                maternal_name = r.get('apellidoMaterno')

                if paternal_name is not None and len(paternal_name) > 0:

                    result = name + ' ' + paternal_name + ' ' + maternal_name

                    if len(result.strip()) != 0:
                        client_obj = Client(
                            names=result,
                        )
                        client_obj.save()

                        client_type_obj = ClientType(
                            document_number=nro_document,
                            client=client_obj,
                            document_type_id=type_document
                        )
                        client_type_obj.save()
                    else:
                        data = {'error': 'NO EXISTE DNI. REGISTRE MANUALMENTE'}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response
                else:
                    data = {
                        'error': 'PROBLEMAS CON LA CONSULTA A LA RENIEC, FAVOR DE INTENTAR MAS TARDE O REGISTRE MANUALMENTE'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

            elif type_document == '06':

                type_name = 'RUC'
                r = query_apis_net_dni_ruc(nro_document, type_name)

                if r.get('numeroDocumento') == nro_document:
                    business_name = r.get('nombre')
                    address_business = r.get('direccion')
                    result = business_name
                    address = address_business

                    client_obj = Client(
                        names=result,
                    )
                    client_obj.save()

                    client_type_obj = ClientType(
                        document_number=nro_document,
                        client=client_obj,
                        document_type_id=type_document
                    )
                    client_type_obj.save()

                    client_address_obj = ClientAddress(
                        address=address,
                        client=client_obj
                    )
                    client_address_obj.save()

        return JsonResponse({'client_id': client_obj.id, 'result': result, 'address': address},
                            status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_purchases_bills(request):
    if request.method == 'GET':
        bill_set = Bill.objects.filter(status='S').order_by('-id')
        bill_dict = []
        for b in bill_set:
            rowspan = b.billdetail_set.count()
            if b.billdetail_set.count() == 0:
                rowspan = 1
            item_bill = {
                'id': b.id,
                'register_date': b.register_date,
                'expiration_date': b.expiration_date,
                'order_number': b.order_number,
                'serial': b.serial,
                'correlative': b.correlative,
                'supplier_name': b.supplier.name,
                'delivery_address': b.delivery_address,
                'bill_base_total': b.bill_base_total,
                'bill_igv_total': b.bill_igv_total,
                'bill_total_total': b.bill_total_total,
                'sum_quantity_invoice': b.sum_quantity_invoice(),
                'sum_quantity_purchased': b.sum_quantity_purchased(),
                'bill_detail': [],
                'row_count': rowspan
            }
            for d in b.billdetail_set.filter(status_quantity='C'):
                item_detail = {
                    'id': d.id,
                    'product': d.product.name,
                    'quantity': str(round(d.quantity, 2)),
                    'unit': d.unit.description,
                    'price_unit': str(round(d.price_unit, 4))
                }
                item_bill.get('bill_detail').append(item_detail)
            bill_dict.append(item_bill)

        return render(request, 'sales/logistic_list.html', {
             'bill_dict': bill_dict,
        })
    return JsonResponse({'message': 'Error de peticion'}, status=HTTPStatus.BAD_REQUEST)


def assign_to_warehouse(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        subsidiary_stores = SubsidiaryStore.objects.filter(category='V')

        bill_obj = Bill.objects.get(id=int(pk))
        bill_details_set = BillDetail.objects.filter(bill=bill_obj)
        unit_description = ''

        details_dict = []

        for bd in bill_details_set:
            product_detail_get = ProductDetail.objects.filter(unit=bd.unit, product=bd.product).last()
            quantity_minimum = product_detail_get.quantity_minimum
            quantity_in_units = bd.quantity * quantity_minimum
            unit_description = bd.unit.description
            item = {
                'id': bd.id,
                'product_id': bd.product.id,
                'product_name': bd.product.name,
                'quantity': bd.quantity,
                'quantity_in_units': str(round(quantity_in_units, 2)),
                'quantity_minimum': str(quantity_minimum),
                'unit_id': bd.unit.id,
                'unit_name': bd.unit.name,
                'unit_description': bd.unit.description,
                'price_unit': str(round(bd.price_unit, 6)),
                'amount': bd.amount(),
                'units_sold': []
            }
            for u in ProductDetail.objects.filter(product_id=bd.product.id).all():
                item_units = {
                    'id': u.id,
                    'unit_id': u.unit.id,
                    'unit_name': u.unit.name,
                    'unit_description': u.unit.description,
                    'quantity_minimum': round(u.quantity_minimum, 0),
                    'price_purchase': str(round(u.price_purchase, 6))
                }
                item.get('units_sold').append(item_units)
            details_dict.append(item)

        t = loader.get_template('sales/assignment_detail_bill.html')
        c = ({
            'formatdate': formatdate,
            'unit_name': unit_description,
            'subsidiary_stores': subsidiary_stores,
            'detail_bill': details_dict,
            'bill_obj': bill_obj,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def save_detail_to_warehouse(request):
    if request.method == 'GET':
        purchase_request = request.GET.get('details', '')
        data_purchase = json.loads(purchase_request)

        assign_date = str(data_purchase["AssignDate"])
        bill_id = int(data_purchase["Bill"])
        bill_obj = Bill.objects.get(id=int(bill_id))

        batch_number = data_purchase["Batch"]
        batch_expiration_date = str(data_purchase["BatchExpirationDate"])
        guide_number = data_purchase["GuideNumber"]
        store = data_purchase["Store"]

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(store))

        bill_obj.batch_number = batch_number
        bill_obj.batch_expiration_date = batch_expiration_date
        bill_obj.guide_number = guide_number
        bill_obj.assign_date = assign_date
        bill_obj.store_destiny = subsidiary_store_obj
        bill_obj.status = 'E'
        bill_obj.save()

        for d in data_purchase['Details']:

            product_id = int(d['Product'])
            product_obj = Product.objects.get(id=product_id)
            unit_id = int(d['UnitPurchase'])
            unit_obj = Unit.objects.get(id=unit_id)
            unit_min_product = ProductDetail.objects.get(product=product_obj, unit=unit_obj).quantity_minimum
            price_purchase = decimal.Decimal(d['PricePurchase'])

            unit_und_obj = Unit.objects.get(name='UND')

            # ----------------------------------- QUANTITY ENTERED --------------------------------------------------

            entered_quantity_principal = decimal.Decimal(d['EnteredQuantityPrincipal'])
            entered_quantity_in_units = entered_quantity_principal * unit_min_product
            entered_quantity_units = d['EnteredQuantityUnits']

            if entered_quantity_principal != 0 and entered_quantity_principal != '':
                detail_entered_obj = BillDetail.objects.create(quantity=entered_quantity_principal, unit=unit_obj,
                                                               price_unit=price_purchase, product=product_obj,
                                                               status_quantity='I', bill=bill_obj)
                try:
                    product_store_obj = ProductStore.objects.get(product=product_obj,
                                                                 subsidiary_store=subsidiary_store_obj)
                except ProductStore.DoesNotExist:
                    product_store_obj = None

                if product_store_obj is None:
                    new_product_store_obj = ProductStore.objects.create(product=product_obj,
                                                                        subsidiary_store=subsidiary_store_obj,
                                                                        stock=entered_quantity_in_units)
                    kardex_initial(new_product_store_obj, entered_quantity_in_units, price_purchase,
                                   bill_detail_obj=detail_entered_obj)
                else:
                    kardex_input(product_store_obj.id, entered_quantity_in_units, price_purchase,
                                 bill_detail_obj=detail_entered_obj)

            if entered_quantity_units != 0 and entered_quantity_units != '':
                detail_entered_units_obj = BillDetail.objects.create(quantity=entered_quantity_units,
                                                                     price_unit=price_purchase, unit=unit_und_obj,
                                                                     product=product_obj, status_quantity='I',
                                                                     bill=bill_obj)
                try:
                    product_store_obj = ProductStore.objects.get(product=product_obj,
                                                                 subsidiary_store=subsidiary_store_obj)
                except ProductStore.DoesNotExist:
                    product_store_obj = None

                if product_store_obj is None:
                    new_product_store_obj = ProductStore.objects.create(product=product_obj,
                                                                        subsidiary_store=subsidiary_store_obj,
                                                                        stock=entered_quantity_units)
                    new_product_store_obj.save()
                    kardex_initial(new_product_store_obj, entered_quantity_units, price_purchase,
                                   bill_detail_obj=detail_entered_units_obj)
                else:
                    kardex_input(product_store_obj.id, entered_quantity_units, price_purchase,
                                 bill_detail_obj=detail_entered_units_obj)

            # ----------------------------------- QUANTITY RETURNED --------------------------------------------------

            returned_quantity_principal = d['ReturnedQuantityPrincipal']
            returned_quantity_units = d['ReturnedQuantityUnits']

            if returned_quantity_principal != 0 and returned_quantity_principal != '':
                BillDetail.objects.create(quantity=returned_quantity_principal, price_unit=price_purchase,
                                          unit=unit_obj, product=product_obj, status_quantity='D', bill=bill_obj)

            if returned_quantity_units != 0 and returned_quantity_units != '':
                BillDetail.objects.create(quantity=returned_quantity_units, price_unit=price_purchase,
                                          unit=unit_und_obj, product=product_obj, status_quantity='D', bill=bill_obj)

            # ----------------------------------- QUANTITY SOLD --------------------------------------------------

            sold_quantity_principal = d['SoldQuantityPrincipal']
            sold_quantity_units = d['SoldQuantityUnit']
            sold_order_id = d['SoldOrderId']
            order_sale_obj = None
            if sold_quantity_principal != 0 and sold_quantity_principal != '':
                order_sale_obj = Order.objects.get(id=int(sold_order_id))
                BillDetail.objects.create(quantity=sold_quantity_principal, price_unit=price_purchase, unit=unit_obj,
                                          product=product_obj, status_quantity='V', bill=bill_obj, order=order_sale_obj)

            if sold_quantity_units != 0 and sold_quantity_units != '':
                order_sale_obj = Order.objects.get(id=int(sold_order_id))
                BillDetail.objects.create(quantity=sold_quantity_units, price_unit=price_purchase, unit=unit_und_obj,
                                          product=product_obj, status_quantity='V', bill=bill_obj, order=order_sale_obj)

        bill_purchase_set = BillPurchase.objects.filter(bill=bill_obj)
        for b in bill_purchase_set:
            purchase_obj = b.purchase
            purchase_obj.status = 'A'
            purchase_obj.save()

        return JsonResponse({
            'message': 'PRODUCTO(S) REGISTRADOS EN ALMACEN',
        }, status=HTTPStatus.OK)


def get_details_by_bill(request):
    if request.method == 'GET':
        bill_id = request.GET.get('bill_id', '')
        bill_obj = Bill.objects.get(pk=int(bill_id))
        details_bill = BillDetail.objects.filter(bill=bill_obj)
        t = loader.get_template('sales/details_bill.html')
        c = ({
            'details_bill': details_bill,
            'bill_obj': bill_obj,
        })
        return JsonResponse({
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)


def get_bills_in_warehouse(request):
    if request.method == 'GET':
        bill_set = Bill.objects.filter(status='E').order_by('-id')
        bill_dict = []
        for b in bill_set:
            rowspan = b.billdetail_set.count()
            if b.billdetail_set.count() == 0:
                rowspan = 1
            item_bill = {
                'id': b.id,
                'register_date': b.register_date,
                'expiration_date': b.expiration_date,
                'order_number': b.order_number,
                'serial': b.serial,
                'correlative': b.correlative,
                'supplier_name': b.supplier.name,
                'delivery_address': b.delivery_address,
                'bill_base_total': b.bill_base_total,
                'bill_igv_total': b.bill_igv_total,
                'bill_total_total': b.bill_total_total,
                'sum_quantity_invoice': b.sum_quantity_invoice(),
                'sum_quantity_purchased': b.sum_quantity_purchased(),
                'status_store': b.status,
                'status_store_text': b.get_status_display(),
                'refund': b.get_quantity_refund(),
                # 'bill_detail': [],
                'row_count': rowspan
            }
            # for d in b.billdetail_set.filter(status_quantity='C'):
            #     item_detail = {
            #         'id': d.id,
            #         'product': d.product.name,
            #         'quantity': str(round(d.quantity, 2)),
            #         'unit': d.unit.description,
            #         'price_unit': str(round(d.price_unit, 4))
            #     }
            #     item_bill.get('bill_detail').append(item_detail)
            bill_dict.append(item_bill)

        return render(request, 'sales/logistic_bill_warehouse.html', {
             'bill_dict': bill_dict,
        })
    return JsonResponse({'message': 'Error de peticion'}, status=HTTPStatus.BAD_REQUEST)


def bill_credit_note(request):
    if request.method == 'GET':
        bill_detail_id = request.GET.get('bill_detail_id', '')
        bill_id = request.GET.get('bill_id', '')
        bill_obj = Bill.objects.get(id=int(bill_id))
        bill_detail_obj = BillDetail.objects.get(id=int(bill_detail_id))
        bill_serial = bill_obj.serial
        bill_correlative = bill_obj.correlative
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")
        t = loader.get_template('buys/modal_credit_note.html')
        c = ({
            'bill_detail_obj': bill_detail_obj,
            'bill_serial': bill_serial,
            'bill_correlative': bill_correlative,
            'bill_obj': bill_obj,
            'date': date_now,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def bill_create_credit_note(request):
    if request.method == 'POST':
        nro_document = request.POST.get('nro-document', '')
        date_issue = request.POST.get('date-issue', '')
        bill_id = request.POST.get('bill', '')
        bill_serial = request.POST.get('bill-serial', '')
        bill_correlative = request.POST.get('bill-correlative', '')
        detail = json.loads(request.POST.get('detail', ''))
        # purchase_obj = None
        # purchase_detail_id = ''
        # for detail in detail:
        #     purchase_detail_id = int(detail['purchaseDetail'])
        #     purchase_detail_obj = PurchaseDetail.objects.get(id=int(purchase_detail_id))
        #     purchase_obj = purchase_detail_obj.purchase
        bill_obj = Bill.objects.get(id=int(bill_id))
        CreditNote.objects.create(nro_document=nro_document, issue_date=date_issue, bill=bill_obj)

        return JsonResponse({
            'message': 'Nota de Credito registrada',
            # 'parent': purchase_obj.id,
            # 'purchase_detail_id': purchase_detail_id,
            'nro_document': nro_document,
            'bill': str(bill_obj)
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_sales_list(request, guide=None):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if guide is not None:
        guide_obj = Guide.objects.get(id=int(guide))
        guide_detail_set = GuideDetail.objects.filter(guide=guide_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, accounting_account__code__startswith='101')
        cash_deposit_set = Cash.objects.filter(accounting_account__code__startswith='104')
        error = ""
        sales_store = ""
        if subsidiary_obj is None:
            error = "No tiene una Sede o Almacen para vender"
        else:
            sales_store = SubsidiaryStore.objects.filter(
                subsidiary=subsidiary_obj, category='V').first()
        return render(request, 'sales/sales_list.html', {
            'choices_payments': [(k, v) for k, v in TransactionPayment._meta.get_field('type').choices
                                 if k not in ['EC', 'L', 'Y']],
            'formatdate': formatdate,
            'document_types': DocumentType.objects.all(),
            'error': error,
            'sales_store': sales_store,
            'cash_set': cash_set,
            'cash_deposit_set': cash_deposit_set,
            'guide_obj': guide_obj,
            'subsidiary_obj': subsidiary_obj,
            'guide_detail_set': guide_detail_set,
            'series_set': Subsidiary.objects.filter(id=subsidiary_obj.id),
            'order_set': Order._meta.get_field('order_type').choices,
            'users': User.objects.filter(is_superuser=False, is_staff=True)
        })
    return JsonResponse({'message': 'Error actualice o contacte con sistemas.'}, status=HTTPStatus.BAD_REQUEST)























