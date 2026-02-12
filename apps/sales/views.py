import pytz
from django.db.models.functions import Coalesce, Cast
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View, CreateView, UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponse
from http import HTTPStatus
from .format_dates import validate
from django.db.models import Q, Case, When
from .models import *
from .forms import *
from apps.hrm.models import Subsidiary, District, DocumentType, Employee, Worker, SubsidiarySerial, Province, Department
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
from django.db import DatabaseError, IntegrityError, transaction
from django.core import serializers
from apps.sales.views_SUNAT import send_bill_nubefact, send_receipt_nubefact, query_apis_net_dni_ruc
from apps.sales.number_to_letters import numero_a_letras, numero_a_moneda
from django.utils import timezone
from django.db.models import Min, Sum, Max, Q, F, Prefetch, Subquery, OuterRef, Value, IntegerField
from django.db.models.functions import Greatest
from django.db.models.functions import (
    ExtractDay, ExtractMonth, ExtractQuarter, ExtractWeek,
    ExtractWeekDay, ExtractIsoYear, ExtractYear,
)

from ..accounting.models import Bill, BillPurchase, BillDetail, BillDetailBatch
from ..buys.models import PurchaseDetail, Purchase, CreditNote, ContractDetail, CreditNoteDetail
from apps.sales.funtions import *


# class Home(TemplateView):
#     template_name = 'sales/home.html'


class ProductList(View):
    model = Product
    form_class = FormProduct
    template_name = 'sales/product_list.html'

    def get_queryset(self, is_enabled=True):
        last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]

        return self.model.objects.filter(
            is_enabled=is_enabled
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
            'products_active': self.get_queryset(is_enabled=True),
            'products_inactive': self.get_queryset(is_enabled=False),
            'subsidiary': subsidiary_obj,
            'form': self.form_class
        }
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class JsonProductList(View):
    def get(self, request):
        products = Product.objects.filter(is_enabled=True).order_by('id')
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
        subsidiaries = Subsidiary.objects.all()
        subsidiaries_stores = SubsidiaryStore.objects.all()
        t = loader.get_template('sales/kardex.html')
        c = ({
            'product': product,
            'subsidiaries': subsidiaries,
            'subsidiaries_stores': subsidiaries_stores,
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

        price_purchase_unit = ProductDetail.objects.get(product=product, unit__name='UND').price_purchase

        inventories = None
        if product_store.count() > 0:
            inventories = Kardex.objects.filter(
                product_store=product_store[0], create_at__date__range=[start_date, end_date]
            ).select_related(
                'product_store__product',
                'order_detail__order',
                'guide_detail__guide__guide_motive',
            ).order_by('id')

            # Summary calculations
            initial_units = decimal.Decimal(0)
            initial_valorized = decimal.Decimal(0)
            purchase_units = decimal.Decimal(0)
            purchase_valorized = decimal.Decimal(0)
            final_units = decimal.Decimal(0)
            final_valorized = decimal.Decimal(0)

            if inventories:
                for k in inventories:
                    if k.type_operation == '16':
                        initial_units += k.remaining_quantity
                        initial_valorized += k.remaining_price_total
                    if k.operation == 'E':
                        purchase_units += k.quantity
                        purchase_valorized += k.price_total

                last_record = inventories.last()
                final_units = last_record.remaining_quantity
                final_valorized = last_record.remaining_price_total

            cost_sales_units = initial_units + purchase_units - final_units
            cost_sales_valorized = initial_valorized + purchase_valorized - final_valorized

            summary = {
                'initial_units': initial_units,
                'initial_valorized': initial_valorized,
                'purchase_units': purchase_units,
                'purchase_valorized': purchase_valorized,
                'final_units': final_units,
                'final_valorized': final_valorized,
                'cost_sales_units': cost_sales_units,
                'cost_sales_valorized': cost_sales_valorized
            }

        t = loader.get_template('sales/kardex_grid_list.html')
        c = ({'product': product, 'inventories': inventories, 'summary': summary})

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
        contexto['provinces'] = Province.objects.all()
        contexto['departments'] = Department.objects.all()
        contexto['subsidiaries'] = Subsidiary.objects.all()
        contexto['type_client'] = Client._meta.get_field('type_client').choices
        contexto['type_address'] = ClientAddress._meta.get_field('type_address').choices
        contexto['price_types'] = PriceType.objects.filter(is_enabled=True)
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

        price_type_id = data_client.get("price_type", '')
        price_type_obj = None
        if price_type_id and str(price_type_id) != '' and str(price_type_id) != '0':
            try:
                price_type_obj = PriceType.objects.get(id=int(price_type_id))
            except PriceType.DoesNotExist:
                pass

        client_obj = Client(
            names=names.upper(),
            phone=phone,
            email=email,
            cod_siaf=siaf,
            type_client=type_client,
            price_type=price_type_obj
        )
        client_obj.save()

        client_type_obj = ClientType(
            client=client_obj,
            document_type=document_type_obj,
            document_number=document_number
        )
        client_type_obj.save()

        if type_client == 'PU':
            # Manejar múltiples direcciones para clientes públicos
            if 'Addresses' in data_client and len(data_client['Addresses']) > 0:
                # Si viene en formato de array (múltiples direcciones)
                has_main_address = False
                addresses_to_save = []

                for d in data_client['Addresses']:
                    new_address = str(d.get('new_address', d.get('publicAddress', '')))
                    district = str(d.get('district', d.get('publicDistrict', '')))
                    province = str(d.get('province', d.get('publicProvince', '')))
                    department = str(d.get('department', d.get('publicDepartment', '')))
                    type_address = str(d.get('type_address', 'P'))

                    # Validar que al menos una sea principal
                    if type_address == 'P':
                        has_main_address = True

                    district_obj = District.objects.get(id=district) if district and district != '0' else None
                    province_obj = Province.objects.get(id=province) if province and province != '0' else None
                    department_obj = Department.objects.get(id=department) if department and department != '0' else None

                    client_address_obj = ClientAddress(
                        client=client_obj,
                        address=new_address.upper(),
                        district=district_obj,
                        province=province_obj,
                        department=department_obj,
                        type_address=type_address
                    )
                    addresses_to_save.append((client_address_obj, type_address))

                # Si no hay dirección principal, marcar la primera como principal
                if not has_main_address and addresses_to_save:
                    addresses_to_save[0][0].type_address = 'P'

                # Guardar todas las direcciones
                for addr_obj, _ in addresses_to_save:
                    addr_obj.save()
            else:
                # Formato antiguo (una sola dirección)
                public_address = str(data_client.get("publicAddress", ''))
                public_district = str(data_client.get("publicDistrict", ''))
                public_province = str(data_client.get("publicProvince", ''))
                public_department = str(data_client.get("publicDepartment", ''))
                type_address = str(data_client.get("type_address", 'P'))

                if public_address:
                    district_obj = District.objects.get(
                        id=public_district) if public_district and public_district != '0' else None
                    province_obj = Province.objects.get(
                        id=public_province) if public_province and public_province != '0' else None
                    department_obj = Department.objects.get(
                        id=public_department) if public_department and public_department != '0' else None

                    client_address_obj = ClientAddress(
                        client=client_obj,
                        address=public_address.upper(),
                        district=district_obj,
                        province=province_obj,
                        department=department_obj,
                        type_address=type_address
                    )
                    client_address_obj.save()

        elif type_client == 'PR':
            has_main_address = False
            addresses_to_save = []

            for d in data_client['Addresses']:
                new_address = str(d['new_address'])
                district = str(d.get('district', ''))
                province = str(d.get('province', ''))
                department = str(d.get('department', ''))
                type_address = str(d.get('type_address', 'P'))

                # Validar que al menos una sea principal
                if type_address == 'P':
                    has_main_address = True

                district_obj = District.objects.get(id=district) if district and district != '0' else None
                province_obj = Province.objects.get(id=province) if province and province != '0' else None
                department_obj = Department.objects.get(id=department) if department and department != '0' else None

                client_address_obj = ClientAddress(
                    client=client_obj,
                    address=new_address.upper(),
                    district=district_obj,
                    province=province_obj,
                    department=department_obj,
                    type_address=type_address
                )
                addresses_to_save.append((client_address_obj, type_address))

            # Si no hay dirección principal, marcar la primera como principal
            if not has_main_address and addresses_to_save:
                addresses_to_save[0][0].type_address = 'P'

            # Guardar todas las direcciones
            for addr_obj, _ in addresses_to_save:
                addr_obj.save()

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
            # series_set = Subsidiary.objects.all()
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
            context['series'] = SubsidiarySerial.objects.filter(subsidiary=subsidiary_obj)
            context['document_types'] = document_types
            context['date'] = formatdate
            context['choices_payments'] = [(k, v) for k, v in TransactionPayment._meta.get_field('type').choices
                                           if k not in selected_choices]
            # context['series'] = series_set
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


def get_correlative(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        serial = request.GET.get('serial', '')
        correlative = get_correlative_by_subsidiary(subsidiary_obj=subsidiary_obj, serial=serial)

        return JsonResponse({'correlative': correlative}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_correlative_by_subsidiary(subsidiary_obj=None, serial=None):
    result = ''
    search = SubsidiarySerial.objects.filter(subsidiary=subsidiary_obj, serial=serial)
    if search.exists():
        subsidiary_serial_obj = search.last()
        correlative = subsidiary_serial_obj.correlative
        correlative = correlative + 1
        result = str(correlative).zfill(6)
    return result


@csrf_exempt
def save_order(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user_id = request.user.id
                user_obj = User.objects.get(id=user_id)
                subsidiary_obj = get_subsidiary_by_user(user_obj)

                _order_id = request.POST.get('order', '')
                _guide_id = request.POST.get('guide_id', '')
                _client_id = request.POST.get('client-id', '')
                _type_payment = request.POST.get('transaction_payment_type', '')
                # _serial = request.POST.get('serial', '')
                _serial_text = request.POST.get('serial_text', '')
                _correlative = request.POST.get('correlative', '')
                _observation = request.POST.get('observation', '')
                _type_document = request.POST.get('type_document', '')
                _date = request.POST.get('date', '')
                _sum_total = request.POST.get('sum-total', '')

                _condition_days = request.POST.get('condition_days', '')
                _order_buy = request.POST.get('order_buy', '')
                _cod_unit_exe = request.POST.get('cod_unit_exe', '')
                _n_contract = request.POST.get('n_contract', '')

                subsidiary_store_sales_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
                client_obj = Client.objects.get(pk=int(_client_id))

                detail = json.loads(request.POST.get('detail', ''))
                credit = json.loads(request.POST.get('credit', ''))

                if _order_id == '':
                    order_obj = Order(
                        order_type='V',
                        client=client_obj,
                        serial=_serial_text,
                        user=user_obj,
                        total=decimal.Decimal(_sum_total),
                        status='C',
                        # subsidiary_store=subsidiary_store_sales_obj,
                        subsidiary=subsidiary_obj,
                        create_at=_date,
                        # correlative=get_correlative_order(subsidiary_obj, 'V'),
                        correlative=_correlative,
                        way_to_pay_type=_type_payment,
                        observation=_observation,
                        type_document=_type_document,
                        pay_condition=_condition_days,
                        order_buy=_order_buy
                    )
                    order_obj.save()

                    for detail in detail:
                        product_id = int(detail['product'])
                        commentary = str(detail['commentary'])
                        unit_id = int(detail['unit'])
                        quantity = decimal.Decimal(detail['quantity'])
                        price = decimal.Decimal(detail['price'])
                        total = decimal.Decimal(detail['detailTotal'])
                        store_product_id = int(detail['store'])
                        batch_id = detail['batch']
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
                            status='V',
                            commentary=commentary,
                            product_store=product_store_obj
                        )
                        order_detail_obj.save()
                        if _type_document == 'F':
                            type_document = '01'
                        elif _type_payment == 'B':
                            type_document = '03'
                        else:
                            type_document = '00'

                        # Manejar múltiples lotes separados por comas
                        if batch_id != '0' and batch_id != '':
                            # Si hay múltiples lotes separados por comas
                            if ',' in str(batch_id):
                                batch_ids = [bid.strip() for bid in str(batch_id).split(',')]
                                # Obtener los lotes y sus cantidades desde GuideDetailBatch
                                guide_detail_id = detail.get('guide_detail', '')
                                if guide_detail_id:
                                    guide_detail_obj = GuideDetail.objects.get(id=guide_detail_id)
                                    batch_details = guide_detail_obj.batch_details.all()

                                    # Usar la nueva función para múltiples lotes
                                    kardex_ouput_multi_batch(
                                        product_store_obj.id,
                                        quantity_minimum_unit,
                                        order_detail_obj=order_detail_obj,
                                        type_document=type_document,
                                        type_operation='01',
                                        batch_details=batch_details
                                    )
                                else:
                                    # Fallback: usar el primer lote disponible
                                    first_batch_id = batch_ids[0]
                                    batch_obj = Batch.objects.get(id=int(first_batch_id))
                                    kardex_ouput(product_store_obj.id, quantity_minimum_unit,
                                                 order_detail_obj=order_detail_obj, type_document=type_document,
                                                 type_operation='01', batch_obj=batch_obj)
                            else:
                                # Un solo lote
                                batch_obj = Batch.objects.get(id=int(batch_id))
                                kardex_ouput(product_store_obj.id, quantity_minimum_unit,
                                             order_detail_obj=order_detail_obj, type_document=type_document,
                                             type_operation='01', batch_obj=batch_obj)
                        else:
                            # Sin lote específico, usar el lote con menor número
                            min_batch_number = Batch.objects.filter(
                                product_store=product_store_obj).aggregate(Min('batch_number'))['batch_number__min']

                            batch_obj = Batch.objects.filter(product_store=product_store_obj,
                                                             batch_number=min_batch_number).order_by('id').last()

                            kardex_ouput(product_store_obj.id, quantity_minimum_unit, order_detail_obj=order_detail_obj,
                                         type_document=type_document, type_operation='01', batch_obj=batch_obj)

                        guide_detail_id = detail['guide_detail']
                        if guide_detail_id:
                            guide_detail_obj = GuideDetail.objects.get(id=guide_detail_id)
                            kardex_obj = Kardex.objects.get(order_detail=order_detail_obj)
                            kardex_obj.guide_detail = guide_detail_obj
                            kardex_obj.save()

                else:
                    order_obj = save_order_with_order_id(_order_id, client_obj, _serial_text, user_obj, _sum_total,
                                                         _date,
                                                         _correlative, _type_payment, _observation, _type_document,
                                                         detail)

                code_operation = '-'
                cash_obj = None
                if _type_payment in ['E', 'D']:
                    cash_id = request.POST.get('cash_id' if _type_payment == 'E' else 'id_cash_deposit', '')
                    cash_obj = Cash.objects.get(id=int(cash_id))

                    if _type_payment == 'D':
                        code_operation = request.POST.get('code-operation', '')

                    loan_payment_obj = LoanPayment(
                        pay=decimal.Decimal(_sum_total),
                        order=order_obj,
                        create_at=_date,
                        type='V',
                        operation_date=_date
                    )
                    loan_payment_obj.save()

                    transaction_payment_obj = TransactionPayment(
                        payment=decimal.Decimal(_sum_total),
                        type=_type_payment,
                        operation_code=code_operation,
                        loan_payment=loan_payment_obj
                    )
                    transaction_payment_obj.save()

                    cash_flow_obj = CashFlow(
                        transaction_date=_date,
                        description=f"{order_obj.subsidiary.serial}-{str(order_obj.correlative).zfill(6)}",
                        document_type_attached='T',
                        type=_type_payment,
                        total=_sum_total,
                        operation_code=code_operation,
                        order=order_obj,
                        user=user_obj,
                        cash=cash_obj
                    )
                    cash_flow_obj.save()

                elif _type_payment == 'C':
                    for c in credit:
                        PaymentFees.objects.create(date=c['date'], order=order_obj,
                                                   amount=decimal.Decimal(c['amount']))

                correlative_no_zeros = _correlative.lstrip('0')
                subsidiary_serial = SubsidiarySerial.objects.filter(subsidiary=subsidiary_obj, serial=_serial_text,
                                                                    type_document=_type_document).last()
                subsidiary_serial.correlative = int(correlative_no_zeros)
                subsidiary_serial.save()

                if _guide_id:
                    guide_obj = Guide.objects.get(pk=int(_guide_id))
                    contract_detail_obj = ContractDetail.objects.get(id=guide_obj.contract_detail.id)
                    contract_detail_obj.order = order_obj
                    contract_detail_obj.save()

                return JsonResponse({
                    'message': 'Venta generada',
                    'order_id': order_obj.id,
                    'guide': _guide_id
                }, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse({
                'message': f'Error al guardar la orden: {str(e)}',
                'error': True
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def save_order_with_order_id(order_id, client_obj, _serial_text, user_obj, _sum_total, _date, _correlative,
                             _type_payment, _observation, _type_document, detail):
    order_obj = Order.objects.get(id=int(order_id))
    order_obj.client = client_obj
    order_obj.serial = _serial_text
    order_obj.user = user_obj
    order_obj.total = decimal.Decimal(_sum_total)
    order_obj.status = 'C'
    order_obj.create_at = _date
    order_obj.correlative = _correlative
    order_obj.way_to_pay_type = _type_payment
    order_obj.observation = _observation
    order_obj.type_document = _type_document
    order_obj.save()

    # Venta Almacén (VA): la salida ya se registró en kardex y batch al momento de la venta.
    # Solo actualizar datos de la orden y detalles, sin volver a registrar kardex.
    is_warehouse_sale = order_obj.sale_type == 'VA'

    for d in detail:
        detail_id = int(d['detail'])
        if detail_id:
            detail_obj = OrderDetail.objects.get(id=int(detail_id))
            detail_obj.price_unit = decimal.Decimal(d['price'])
            detail_obj.status = 'V'
            detail_obj.commentary = detail_obj.product.name + ' - ' + detail_obj.product.product_brand.name
            detail_obj.save()

            if not is_warehouse_sale:
                quantity_minimum_unit = calculate_minimum_unit(detail_obj.quantity_sold, detail_obj.unit,
                                                               detail_obj.product)
                product_store_obj = detail_obj.product_store
                if _type_document == 'F':
                    type_document = '01'
                elif _type_payment == 'B':
                    type_document = '03'
                else:
                    type_document = '00'

                # Manejar múltiples lotes separados por comas
                batch_id = d.get('batch', '0')
                if batch_id != '0' and batch_id != '':
                    # Si hay múltiples lotes separados por comas
                    if ',' in str(batch_id):
                        batch_ids = [bid.strip() for bid in str(batch_id).split(',')]
                        # Obtener los lotes y sus cantidades desde GuideDetailBatch
                        guide_detail_id = d.get('guide_detail', '')
                        if guide_detail_id:
                            guide_detail_obj = GuideDetail.objects.get(id=guide_detail_id)
                            batch_details = guide_detail_obj.batch_details.all()

                            # Usar la nueva función para múltiples lotes
                            kardex_ouput_multi_batch(
                                product_store_obj.id,
                                quantity_minimum_unit,
                                order_detail_obj=detail_obj,
                                type_document=type_document,
                                type_operation='01',
                                batch_details=batch_details
                            )
                        else:
                            # Fallback: usar el primer lote disponible
                            first_batch_id = batch_ids[0]
                            batch_obj = Batch.objects.get(id=int(first_batch_id))
                            kardex_ouput(product_store_obj.id, quantity_minimum_unit,
                                         order_detail_obj=detail_obj, type_document=type_document,
                                         type_operation='01', batch_obj=batch_obj)
                    else:
                        # Un solo lote
                        batch_obj = Batch.objects.get(id=int(batch_id))
                        kardex_ouput(product_store_obj.id, quantity_minimum_unit,
                                     order_detail_obj=detail_obj, type_document=type_document,
                                     type_operation='01', batch_obj=batch_obj)
                else:
                    # Sin lote específico, usar el lote con menor número
                    min_batch_number = Batch.objects.filter(
                        product_store=product_store_obj).aggregate(Min('batch_number'))['batch_number__min']

                    batch_obj = Batch.objects.filter(product_store=product_store_obj,
                                                     batch_number=min_batch_number).order_by('id').last()

                    kardex_ouput(product_store_obj.id, quantity_minimum_unit, order_detail_obj=detail_obj,
                                 type_document=type_document, type_operation='01', batch_obj=batch_obj)
        else:
            # Detalles nuevos: solo para ventas que no son de almacén (VA)
            if is_warehouse_sale:
                continue  # VA: no se agregan detalles nuevos, la venta ya está registrada

            product_id = int(d['product'])
            unit_id = int(d['unit'])
            quantity = decimal.Decimal(d['quantity'])
            price = decimal.Decimal(d['price'])
            store_product_id = int(d['store'])

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
                status='V',
                commentary=product_obj.name + ' - ' + product_obj.product_brand.name
            )
            order_detail_obj.save()

            _type_document = order_detail_obj.order.type_document

            if _type_document == 'F':
                type_document = '01'
            elif _type_payment == 'B':
                type_document = '03'
            else:
                type_document = '00'

            # Manejar múltiples lotes separados por comas
            batch_id = d.get('batch', '0')
            if batch_id != '0' and batch_id != '':
                # Si hay múltiples lotes separados por comas
                if ',' in str(batch_id):
                    batch_ids = [bid.strip() for bid in str(batch_id).split(',')]
                    # Obtener los lotes y sus cantidades desde GuideDetailBatch
                    guide_detail_id = d.get('guide_detail', '')
                    if guide_detail_id:
                        guide_detail_obj = GuideDetail.objects.get(id=guide_detail_id)
                        batch_details = guide_detail_obj.batch_details.all()

                        # Usar la nueva función para múltiples lotes
                        kardex_ouput_multi_batch(
                            product_store_obj.id,
                            quantity_minimum_unit,
                            order_detail_obj=order_detail_obj,
                            type_document=type_document,
                            type_operation='01',
                            batch_details=batch_details
                        )
                    else:
                        # Fallback: usar el primer lote disponible
                        first_batch_id = batch_ids[0]
                        batch_obj = Batch.objects.get(id=int(first_batch_id))
                        kardex_ouput(product_store_obj.id, quantity_minimum_unit,
                                     order_detail_obj=order_detail_obj, type_document=type_document,
                                     type_operation='01', batch_obj=batch_obj)
                else:
                    # Un solo lote
                    batch_obj = Batch.objects.get(id=int(batch_id))
                    kardex_ouput(product_store_obj.id, quantity_minimum_unit,
                                 order_detail_obj=order_detail_obj, type_document=type_document,
                                 type_operation='01', batch_obj=batch_obj)
            else:
                # Sin lote específico, usar el lote con menor número
                min_batch_number = Batch.objects.filter(
                    product_store=product_store_obj).aggregate(Min('batch_number'))['batch_number__min']

                batch_obj = Batch.objects.filter(product_store=product_store_obj,
                                                 batch_number=min_batch_number).order_by('id').last()

                kardex_ouput(product_store_obj.id, quantity_minimum_unit, order_detail_obj=order_detail_obj,
                             type_document=type_document, type_operation='01', batch_obj=batch_obj)

    return order_obj


def calculate_minimum_unit(quantity, unit_obj, product_obj):
    product_detail_sent = ProductDetail.objects.get(product=product_obj, unit=unit_obj)
    new_quantity = quantity * product_detail_sent.quantity_minimum
    return new_quantity


def kardex_initial(
        product_store_obj,
        stock,
        price_unit,
        bill_detail_obj=None,
        order_detail_obj=None,
        guide_detail_obj=None,
):
    kardex_obj = Kardex.objects.create(
        operation='C',
        quantity=0,
        price_unit=0,
        price_total=0,
        remaining_quantity=decimal.Decimal(stock),
        remaining_price=decimal.Decimal(price_unit),
        remaining_price_total=decimal.Decimal(stock) * decimal.Decimal(price_unit),
        order_detail=order_detail_obj,
        product_store=product_store_obj,
        guide_detail=guide_detail_obj,
        bill_detail=bill_detail_obj,
        type_document='00',
        type_operation='16'
    )

    return kardex_obj


def kardex_input(
        product_store_id,
        quantity,
        total_cost,
        order_detail_obj=None,
        guide_detail_obj=None,
        bill_detail_obj=None,
        type_document='00',
        type_operation='99',
        credit_note_detail_obj=None,
        credit_note_order_detail_obj=None
        # distribution_detail_obj=None,
):
    product_store = ProductStore.objects.get(pk=int(product_store_id))
    old_stock = product_store.stock
    new_stock = old_stock + quantity

    price_unit = decimal.Decimal(total_cost) / quantity

    # new_quantity = decimal.Decimal(quantity_purchased)
    # new_price_unit = decimal.Decimal(price_unit)
    # new_price_total = quantity * new_price_unit

    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).last()
    last_remaining_quantity = last_kardex.remaining_quantity
    last_remaining_price_total = last_kardex.remaining_price_total
    old_price_unit = last_kardex.remaining_price
    # print(old_price_unit)
    new_remaining_quantity = last_remaining_quantity + quantity
    new_remaining_price = (decimal.Decimal(last_remaining_price_total) +
                           total_cost) / new_remaining_quantity
    new_remaining_price_total = new_remaining_quantity * new_remaining_price

    kardex_obj = Kardex.objects.create(
        operation='E',
        quantity=quantity,
        price_unit=price_unit,
        price_total=total_cost,
        remaining_quantity=new_remaining_quantity,
        remaining_price=new_remaining_price,
        remaining_price_total=new_remaining_price_total,
        guide_detail=guide_detail_obj,
        order_detail=order_detail_obj,
        product_store=product_store,
        bill_detail=bill_detail_obj,
        type_document=type_document,
        type_operation=type_operation,
        credit_note_detail=credit_note_detail_obj,
        credit_note_order_detail=credit_note_order_detail_obj
    )

    product_store.stock = new_stock
    product_store.save()

    return kardex_obj


def kardex_ouput(
        product_store_id,
        quantity,
        # total_cost,
        order_detail_obj=None,
        guide_detail_obj=None,
        bill_detail_obj=None,
        type_document='00',
        type_operation='99',
        credit_note_detail_obj=None,
        batch_obj=None,
        picking_detail=None
        # distribution_detail_obj=None,
):
    product_store = ProductStore.objects.get(pk=int(product_store_id))
    old_stock = product_store.stock
    new_stock = old_stock - decimal.Decimal(quantity)
    # price_unit = decimal.Decimal(total_cost) / quantity
    # new_quantity = decimal.Decimal(quantity)
    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).last()
    last_remaining_quantity = last_kardex.remaining_quantity
    # last_remaining_price_total = last_kardex.remaining_price_total
    old_price_unit = last_kardex.remaining_price
    total_cost = decimal.Decimal(quantity) * old_price_unit
    # new_price_total = old_price_unit * quantity

    new_remaining_quantity = last_remaining_quantity - quantity
    new_remaining_price = last_kardex.remaining_price
    new_remaining_price_total = new_remaining_quantity * new_remaining_price

    kardex_obj = Kardex.objects.create(
        operation='S',
        quantity=quantity,
        price_unit=old_price_unit,
        price_total=total_cost,
        remaining_quantity=new_remaining_quantity,
        remaining_price=new_remaining_price,
        remaining_price_total=new_remaining_price_total,
        guide_detail=guide_detail_obj,
        order_detail=order_detail_obj,
        product_store=product_store,
        bill_detail=bill_detail_obj,
        type_document=type_document,
        type_operation=type_operation,
        credit_note_detail=credit_note_detail_obj,
        picking_detail=picking_detail
    )

    Batch.objects.create(
        batch_number=batch_obj.batch_number,
        expiration_date=batch_obj.expiration_date,
        quantity=decimal.Decimal(quantity),
        remaining_quantity=batch_obj.remaining_quantity - decimal.Decimal(quantity),
        kardex=kardex_obj,
        product_store=product_store
    )

    product_store.stock = new_stock
    product_store.save()


def kardex_ouput_multi_batch(
        product_store_id,
        total_quantity,
        order_detail_obj=None,
        guide_detail_obj=None,
        bill_detail_obj=None,
        type_document='00',
        type_operation='99',
        credit_note_detail_obj=None,
        batch_details=None,
        picking_detail=None
):
    """
    Función para manejar salida de kardex con múltiples lotes.
    Crea un solo registro de Kardex con la cantidad total y descuenta cada lote por separado.
    """
    product_store = ProductStore.objects.get(pk=int(product_store_id))
    old_stock = product_store.stock
    new_stock = old_stock - decimal.Decimal(total_quantity)

    # Obtener el último kardex para calcular precios
    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).last()
    last_remaining_quantity = last_kardex.remaining_quantity
    old_price_unit = last_kardex.remaining_price
    total_cost = decimal.Decimal(total_quantity) * old_price_unit

    new_remaining_quantity = last_remaining_quantity - total_quantity
    new_remaining_price = last_kardex.remaining_price
    new_remaining_price_total = new_remaining_quantity * new_remaining_price

    # Crear un solo registro de Kardex con la cantidad total
    kardex_obj = Kardex.objects.create(
        operation='S',
        quantity=total_quantity,
        price_unit=old_price_unit,
        price_total=total_cost,
        remaining_quantity=new_remaining_quantity,
        remaining_price=new_remaining_price,
        remaining_price_total=new_remaining_price_total,
        guide_detail=guide_detail_obj,
        order_detail=order_detail_obj,
        product_store=product_store,
        bill_detail=bill_detail_obj,
        type_document=type_document,
        type_operation=type_operation,
        credit_note_detail=credit_note_detail_obj,
        picking_detail=picking_detail
    )

    # Descontar cada lote por separado
    if batch_details:
        for batch_detail in batch_details:
            batch_obj = batch_detail.batch
            batch_quantity = batch_detail.quantity

            # Crear registro de Batch con la cantidad específica del lote
            Batch.objects.create(
                batch_number=batch_obj.batch_number,
                expiration_date=batch_obj.expiration_date,
                quantity=decimal.Decimal(batch_quantity),
                remaining_quantity=batch_obj.remaining_quantity - decimal.Decimal(batch_quantity),
                kardex=kardex_obj,
                product_store=product_store
            )

            # Actualizar la cantidad restante del lote original
            batch_obj.remaining_quantity -= decimal.Decimal(batch_quantity)
            batch_obj.save()

    # Actualizar el stock del producto
    product_store.stock = new_stock
    product_store.save()

    return kardex_obj


def kardex_credit_note_input(
        product_store_id,
        quantity,
        total_cost,
        type_document='00',
        type_operation='99',
        credit_note_detail_obj=None
):
    product_store = ProductStore.objects.get(pk=int(product_store_id))
    old_stock = product_store.stock
    new_stock = old_stock - decimal.Decimal(quantity)
    last_kardex = Kardex.objects.filter(product_store_id=product_store.id).last()
    last_remaining_quantity = last_kardex.remaining_quantity
    last_remaining_price_total = last_kardex.remaining_price_total
    price_unit = decimal.Decimal(total_cost) / decimal.Decimal(quantity)
    new_remaining_quantity = last_remaining_quantity - quantity
    new_remaining_price = (last_remaining_price_total + total_cost) / new_remaining_quantity
    new_remaining_price_total = new_remaining_quantity * new_remaining_price

    Kardex.objects.create(
        operation='E',
        quantity=-quantity,
        price_unit=price_unit,
        price_total=-total_cost,
        remaining_quantity=new_remaining_quantity,
        remaining_price=new_remaining_price,
        remaining_price_total=new_remaining_price_total,
        product_store=product_store,
        type_document=type_document,
        type_operation=type_operation,
        credit_note_detail=credit_note_detail_obj
    )

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
            'subsidiary': o.subsidiary.name,
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
        client_id = request.GET.get('client_id', '')
        unit_id = request.GET.get('unit_id', '')

        try:
            if unit_id:
                product_detail_obj = ProductDetail.objects.filter(
                    product_id=int(pk),
                    unit_id=int(unit_id)
                ).first()
            else:
                product_detail_obj = ProductDetail.objects.filter(product_id=int(pk)).first()

            if not product_detail_obj:
                return JsonResponse({'price_unit': 0})

            price = product_detail_obj.price_sale

            # Si hay un cliente, intentar obtener el precio según su tipo de precio
            if client_id:
                try:
                    client_obj = Client.objects.get(id=int(client_id))
                    if client_obj.price_type:
                        try:
                            product_price_obj = ProductPrice.objects.get(
                                price_type=client_obj.price_type,
                                product_detail=product_detail_obj,
                                is_enabled=True
                            )
                            price = product_price_obj.price
                        except ProductPrice.DoesNotExist:
                            pass  # Usar precio por defecto si no existe precio específico
                except Client.DoesNotExist:
                    pass  # Usar precio por defecto si no existe el cliente

        except Exception as e:
            price = 0

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
        client=client_obj, create_at__date__range=[start_date, end_date], order_type__in=['V']
    ).prefetch_related(
        Prefetch(
            'orderdetail_set', queryset=OrderDetail.objects.select_related('product', 'unit').prefetch_related(
                # Prefetch(
                #     'loanpayment_set',
                #     queryset=LoanPayment.objects.select_related('order_detail__order').prefetch_related(
                #         Prefetch(
                #             'transactionpayment_set',
                #             queryset=TransactionPayment.objects.select_related('loan_payment__order_detail__order')
                #         )
                #     )
                # ),
            )
        ),
        Prefetch(
            'cashflow_set', queryset=CashFlow.objects.select_related('cash')
        ),
    ).select_related('subsidiary', 'client').order_by('id')

    dictionary = []

    for o in order_set:
        if o.orderdetail_set.all().exists():
            order_detail_set = o.orderdetail_set.all()
            cash_flow_set = o.cashflow_set.all()
            new = {
                'id': o.id,
                'type': o.get_order_type_display(),
                'client': o.client.names,
                'user': o.user.username,
                'date': o.create_at,
                'order_detail_set': [],
                'status': o.get_status_display(),
                'total': o.total,
                'subtotal': 0,
                # 'total_repay_loan': '{:,}'.format(total_remaining_repay_loan(order_detail_set=order_detail_set).quantize(decimal.Decimal('0.00'),
                #                                                                            rounding=decimal.ROUND_HALF_EVEN)),
                # 'total_remaining_repay_loan': '{:,}'.format(total_remaining_repay_loan(order_detail_set=order_detail_set).quantize(decimal.Decimal('0.00'),
                #                                                                            rounding=decimal.ROUND_HALF_EVEN)),
                'total_spending': '{:,}'.format(
                    total_cash_flow_spending(cashflow_set=cash_flow_set).quantize(decimal.Decimal('0.00'),
                                                                                  rounding=decimal.ROUND_HALF_EVEN)),
                'details_count': order_detail_set.count(),
                'rowspan': 0,
                'has_loans': False
            }
            subtotal = 0

            for d in order_detail_set:
                _type = '-'
                # loan_payment_set = []
                # for lp in d.loanpayment_set.all():
                #     _payment_type = '-'
                #     _cash_flow = None
                #     transaction_payment_set = lp.transactionpayment_set.all()
                #     if transaction_payment_set.exists():
                #         transaction_payment = None
                #         for t in transaction_payment_set:
                #             transaction_payment = t
                #         _cash_flow = get_cash_flow(order=o, transactionpayment=transaction_payment)
                #         _payment_type = transaction_payment.get_type_display()
                #
                #     loan_payment = {
                #         'id': lp.id,
                #         'quantity': lp.quantity,
                #         'date': lp.create_at,
                #         'operation_date': lp.operation_date,
                #         'price': '{:,}'.format(
                #             lp.price.quantize(decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN)),
                #         'type': _payment_type,
                #         'cash_flow': _cash_flow,
                #         'is_review_pay': lp.is_check
                #     }
                #     loan_payment_set.append(loan_payment)

                # loans_count = d.loanpayment_set.all().count()

                # if loans_count == 0:
                #     rowspan = 1
                # else:
                #     rowspan = loans_count
                #     if not new['has_loans']:
                #         new['has_loans'] = True

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
                    # 'repay_loan': '{:,}'.format(round(repay_loan(loan_payment_set=d.loanpayment_set.all())), 2),
                    # 'loan_payment_set': loan_payment_set,
                    # 'loans_count': loans_count,
                    # 'rowspan': rowspan,
                    'has_spending': False
                }
                subtotal += d.quantity_sold * d.price_unit

                new.get('order_detail_set').append(order_detail)
                # new['rowspan'] = new['rowspan'] + rowspan

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
            # sum_total_repay_loan += total_repay_loan(order_detail_set=order_detail_set)
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


def get_products_ajax(request):
    """Autocomplete para buscar productos - retorna en formato jQuery UI Autocomplete"""
    if request.method == 'GET':
        term = request.GET.get('term', '').strip()
        results = []

        try:
            if term and len(term) >= 1:
                # Buscar productos por nombre que contengan el término
                products = Product.objects.filter(
                    Q(name__icontains=term)
                ).values('id', 'name').order_by('name')[:20]

                # Formatear correctamente para jQuery UI Autocomplete
                for product in products:
                    product_name = str(product['name']).strip()
                    if product_name:  # Solo agregar si tiene nombre
                        results.append({
                            'label': product_name,  # Lo que se muestra en el dropdown
                            'value': product_name,  # Lo que se inserta en el input
                            'id': int(product['id']),  # ID para uso interno
                        })
        except Exception as e:
            import traceback
            print(f"Error en autocomplete: {e}")
            print(traceback.format_exc())
            results = []

        # Asegurar que siempre devolvemos un array válido
        return JsonResponse(results, safe=False, status=HTTPStatus.OK)

    return JsonResponse([], safe=False, status=HTTPStatus.BAD_REQUEST)


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
                    subsidiary_id=s.id,
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
                    subsidiary_id=s.id,
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
                    order_detail__order__subsidiary_id=s.id
                ).aggregate(r=Coalesce(Sum('quantity'), 0))
                recovered_dict = {
                    'label': s.name,
                    'y': float(distribution_mobil_set['r'])
                }
                array5.append(recovered_dict)

                # borrowed
                order_detail_set = OrderDetail.objects.filter(
                    order__distribution_mobil__date_distribution__range=[date_initial, date_final],
                    order__subsidiary_id=s.id,
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
                    order__subsidiary_id=s.id,
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
    order_set = Order.objects.filter(subsidiary_id=pk,
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
    totales = Order.objects.filter(subsidiary_id=pk,
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


def get_price_of_product(product_detail_set=None, product=None, unit=None, client=None):
    price = 0
    for pd in product_detail_set:
        if pd.product == product and pd.unit == unit:
            price = pd.price_sale

            # Si hay un cliente con tipo de precio, usar ese precio
            if client and client.price_type:
                try:
                    product_price_obj = ProductPrice.objects.get(
                        price_type=client.price_type,
                        product_detail=pd,
                        is_enabled=True
                    )
                    price = product_price_obj.price
                except ProductPrice.DoesNotExist:
                    pass  # Usar precio por defecto si no existe precio específico
            break
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
            order_type='T',
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
        r=Coalesce(Cast(Max('correlative'), output_field=IntegerField()), Value(0))
    )
    return str(correlative['r'] + 1)


def modal_client_create(request):
    if request.method == 'GET':
        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")

        t = loader.get_template('sales/client_form.html')
        # Optimización: Solo cargar los datos necesarios, los selects se cargarán con AJAX
        c = ({
            'date_now': date_now,
            'districts': [],  # Se cargará con AJAX cuando sea necesario
            'provinces': [],  # Se cargará con AJAX cuando sea necesario
            'departments': [],  # Se cargará con AJAX cuando sea necesario
            'document_types': DocumentType.objects.all(),
            'subsidiaries': Subsidiary.objects.all(),
            'type_client': Client._meta.get_field('type_client').choices,
            'type_address': ClientAddress._meta.get_field('type_address').choices,
            'price_types': PriceType.objects.filter(is_enabled=True)
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

        # Optimización: Solo cargar los datos necesarios para el cliente actual
        # Los demás se cargarán con AJAX cuando sea necesario
        districts_list = []
        provinces_list = []
        departments_list = []

        # Solo cargar los relacionados con las direcciones del cliente
        if client_obj and client_obj.clientaddress_set.exists():
            address_ids = client_obj.clientaddress_set.values_list('district_id', 'province_id', 'department_id')
            district_ids = [a[0] for a in address_ids if a[0]]
            province_ids = [a[1] for a in address_ids if a[1]]
            department_ids = [a[2] for a in address_ids if a[2]]

            if district_ids:
                districts_list = list(District.objects.filter(id__in=district_ids).values('id', 'description'))
            if province_ids:
                provinces_list = list(
                    Province.objects.filter(id__in=province_ids).select_related('department').values('id',
                                                                                                     'description',
                                                                                                     'department_id'))
            if department_ids:
                departments_list = list(Department.objects.filter(id__in=department_ids).values('id', 'description'))

        c = ({
            'client_obj': client_obj,
            'districts': districts_list,  # Solo los relacionados
            'provinces': provinces_list,  # Solo los relacionados
            'departments': departments_list,  # Solo los relacionados
            'type_client': Client._meta.get_field('type_client').choices,
            'document_types': DocumentType.objects.all(),
            'type_address': ClientAddress._meta.get_field('type_address').choices,
            'price_types': PriceType.objects.filter(is_enabled=True)
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

            price_type_id = data_client.get("price_type", '')
            price_type_obj = None
            if price_type_id and str(price_type_id) != '' and str(price_type_id) != '0':
                try:
                    price_type_obj = PriceType.objects.get(id=int(price_type_id))
                except PriceType.DoesNotExist:
                    pass

            client_obj.names = names.upper()
            client_obj.phone = phone
            client_obj.email = email
            client_obj.cod_siaf = siaf
            client_obj.type_client = type_client
            client_obj.price_type = price_type_obj
            client_obj.save()

            client_type_obj = ClientType.objects.get(client=client_obj)
            client_type_obj.document_type = document_type_obj
            client_type_obj.document_number = document_number
            client_type_obj.save()

            client_to_delete = ClientAddress.objects.filter(client=client_obj)
            client_to_delete.delete()

            if type_client == 'PU':
                # Manejar múltiples direcciones para clientes públicos
                if 'Addresses' in data_client and len(data_client['Addresses']) > 0:
                    # Si viene en formato de array (múltiples direcciones)
                    has_main_address = False
                    addresses_to_save = []

                    for d in data_client['Addresses']:
                        new_address = str(d.get('new_address', d.get('publicAddress', '')))
                        district = str(d.get('district', d.get('publicDistrict', '')))
                        province = str(d.get('province', d.get('publicProvince', '')))
                        department = str(d.get('department', d.get('publicDepartment', '')))
                        type_address = str(d.get('type_address', 'P'))

                        # Validar que al menos una sea principal
                        if type_address == 'P':
                            has_main_address = True

                        district_obj = District.objects.get(id=district) if district and district != '0' else None
                        province_obj = Province.objects.get(id=province) if province and province != '0' else None
                        department_obj = Department.objects.get(
                            id=department) if department and department != '0' else None

                        client_address_obj = ClientAddress(
                            client=client_obj,
                            address=new_address.upper(),
                            district=district_obj,
                            province=province_obj,
                            department=department_obj,
                            type_address=type_address
                        )
                        addresses_to_save.append((client_address_obj, type_address))

                    # Si no hay dirección principal, marcar la primera como principal
                    if not has_main_address and addresses_to_save:
                        addresses_to_save[0][0].type_address = 'P'

                    # Guardar todas las direcciones
                    for addr_obj, _ in addresses_to_save:
                        addr_obj.save()
                else:
                    # Formato antiguo (una sola dirección)
                    public_address = str(data_client.get("publicAddress", ''))
                    public_district = str(data_client.get("publicDistrict", ''))
                    public_province = str(data_client.get("publicProvince", ''))
                    public_department = str(data_client.get("publicDepartment", ''))
                    type_address = str(data_client.get("type_address", 'P'))

                    if public_address:
                        district_obj = District.objects.get(
                            id=public_district) if public_district and public_district != '0' else None
                        province_obj = Province.objects.get(
                            id=public_province) if public_province and public_province != '0' else None
                        department_obj = Department.objects.get(
                            id=public_department) if public_department and public_department != '0' else None

                        client_address_obj = ClientAddress(
                            client=client_obj,
                            address=public_address.upper(),
                            district=district_obj,
                            province=province_obj,
                            department=department_obj,
                            type_address=type_address
                        )
                        client_address_obj.save()

            elif type_client == 'PR':
                has_main_address = False
                addresses_to_save = []

                for d in data_client['Addresses']:
                    new_address = str(d['new_address'])
                    district = str(d.get('district', ''))
                    province = str(d.get('province', ''))
                    department = str(d.get('department', ''))
                    type_address = str(d.get('type_address', 'P'))

                    # Validar que al menos una sea principal
                    if type_address == 'P':
                        has_main_address = True

                    district_obj = District.objects.get(id=district) if district and district != '0' else None
                    province_obj = Province.objects.get(id=province) if province and province != '0' else None
                    department_obj = Department.objects.get(id=department) if department and department != '0' else None

                    client_address_obj = ClientAddress(
                        client=client_obj,
                        address=new_address.upper(),
                        district=district_obj,
                        province=province_obj,
                        department=department_obj,
                        type_address=type_address
                    )
                    addresses_to_save.append((client_address_obj, type_address))

                # Si no hay dirección principal, marcar la primera como principal
                if not has_main_address and addresses_to_save:
                    addresses_to_save[0][0].type_address = 'P'

                # Guardar todas las direcciones
                for addr_obj, _ in addresses_to_save:
                    addr_obj.save()

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


def get_departments_ajax(request):
    """Endpoint AJAX para cargar departamentos con búsqueda"""
    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        departments = Department.objects.all()

        if search:
            departments = departments.filter(description__icontains=search)

        departments_list = [{'id': d.id, 'text': d.description} for d in departments[:50]]  # Limitar a 50 resultados

        return JsonResponse({
            'results': departments_list
        }, status=HTTPStatus.OK)
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_provinces_ajax(request):
    """Endpoint AJAX para cargar provincias con búsqueda y filtro por departamento"""
    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        department_id = request.GET.get('department_id', '')

        provinces = Province.objects.select_related('department').all()

        if department_id and department_id != '0':
            provinces = provinces.filter(department_id=department_id)

        if search:
            provinces = provinces.filter(description__icontains=search)

        provinces_list = [{
            'id': p.id,
            'text': p.description,
            'department_id': p.department.id
        } for p in provinces[:50]]  # Limitar a 50 resultados

        return JsonResponse({
            'results': provinces_list
        }, status=HTTPStatus.OK)
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_districts_ajax(request):
    """Endpoint AJAX para cargar distritos con búsqueda y filtro por provincia"""
    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        province_id = request.GET.get('province_id', '')

        districts = District.objects.select_related('province').all()

        if province_id and province_id != '0':
            districts = districts.filter(province_id=province_id)

        if search:
            districts = districts.filter(description__icontains=search)

        districts_list = [{
            'id': d.id,
            'text': d.description,
            'province_id': d.province.id
        } for d in districts[:50]]  # Limitar a 50 resultados

        return JsonResponse({
            'results': districts_list
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
            orders = Order.objects.filter(subsidiary=subsidiary_obj, order_type='T').exclude(status='A')
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
            'type': o.get_order_type_display(),
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
        # sales_store = SubsidiaryStore.objects.filter(
        #     subsidiary=subsidiary_obj, category='V').first()
        # last_kardex = Kardex.objects.filter(product_store=OuterRef('id')).order_by('-id')[:1]
        product_set = None

        value = request.GET.get('value', '')
        barcode = request.GET.get('barcode', '')

        if value != '' and barcode == '':
            array_value = value.split()
            product_query = Product.objects
            full_query = None

            # product_brand_set = ProductBrand.objects.filter(name__icontains=value.upper())

            for i in range(0, len(array_value)):
                q = Q(name__icontains=array_value[i]) | Q(product_brand__name__icontains=array_value[i])
                if full_query is None:
                    full_query = q
                else:
                    full_query = full_query & q

            product_set = product_query.filter(full_query).select_related(
                'product_family', 'product_brand'
            ).prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                        .annotate(
                        is_primary_store=Case(
                            When(subsidiary_store__subsidiary=subsidiary_obj.id, then=Value(0)),
                            default=Value(1),
                            output_field=IntegerField()
                        )
                    )
                        .order_by('is_primary_store', 'id')
                ),
                Prefetch(
                    'productdetail_set', queryset=ProductDetail.objects.select_related('unit')
                ),
            ).order_by('id')

        if value == '' and barcode != '':
            product_set = Product.objects.filter(barcode=barcode).select_related(
                'product_family', 'product_brand'
            ).prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                        .annotate(
                        is_primary_store=Case(
                            When(subsidiary_store__subsidiary=subsidiary_obj.id, then=Value(0)),
                            default=Value(1),
                            output_field=IntegerField()
                        )
                    )
                        .order_by('is_primary_store', 'id')
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
        store_id = int(request.GET.get('store_id', ''))

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        product_store_obj = ProductStore.objects.get(id=store_id)
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
        store = request.GET.get('store', '')
        unit_principal = request.GET.get('unit_principal', '')
        quantity_principal = request.GET.get('input_principal_val', '')
        unit_id = request.GET.get('unit_id', '')
        quantity_unit = request.GET.get('input_units', '')

        create_date = utc_to_local(datetime.now())
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(store))

        order_obj = Order(
            order_type='V',
            status='P',
            sale_type='VA',
            # subsidiary_store=subsidiary_store_obj,
            # correlative=get_correlative_order(subsidiary_obj, 'V'),
            subsidiary=subsidiary_obj,
            create_at=create_date,
            user=user_obj
        )
        order_obj.save()

        product_obj = Product.objects.get(id=int(product_id))
        product_store_obj = ProductStore.objects.get(product=product_obj, subsidiary_store=subsidiary_store_obj)
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
                status='P',
                product_store=product_store_obj,
                commentary=product_obj.name
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
                status='P',
                product_store=product_store_obj,
                commentary=product_obj.name
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


def get_order_by_id(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        order_set = Order.objects.filter(id=int(order_id))
        if order_set.exists():
            order_obj = order_set.first()
            if order_obj.status == 'C' and order_obj.sale_type == 'VA' and order_obj.serial != '':
                return JsonResponse({
                    'success': False,
                    'message': 'La Orden ya se encuentra registrada, ',
                    'bill': 'Comprobante ' + str(order_obj.serial) + '-' + str(order_obj.correlative),
                }, status=HTTPStatus.OK)


def get_order_store(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id', '')
        if not order_id:
            return JsonResponse({
                'success': False,
                'message': 'ID de orden no proporcionado',
            }, status=HTTPStatus.BAD_REQUEST)

        try:
            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            order_set = Order.objects.filter(id=int(order_id), subsidiary=subsidiary_obj)

            if not order_set.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'La Orden no existe',
                }, status=HTTPStatus.OK)

            order_obj = order_set.first()

            # Si la orden ya tiene serial, significa que ya está registrada
            # if order_obj.serial is not None and order_obj.serial != '':
            #     return JsonResponse({
            #         'success': False,
            #         'message': 'La Orden ya se encuentra registrada, ',
            #         'bill': 'Comprobante ' + str(order_obj.serial) + '-' + str(order_obj.correlative),
            #     }, status=HTTPStatus.OK)

            # Verificar que la orden esté en estado pendiente y sea tipo venta almacén
            if order_obj.status != 'P' or order_obj.sale_type != 'VA':
                return JsonResponse({
                    'success': False,
                    'message': 'La Orden ya se encuentra registrada, ',
                    'bill': 'Comprobante ' + str(order_obj.serial) + '-' + str(order_obj.correlative),
                }, status=HTTPStatus.OK)

            # Obtener los detalles de la orden
            order_detail_set = OrderDetail.objects.filter(order=order_obj).select_related(
                'product', 'unit', 'product_store', 'product_store__subsidiary_store'
            )
            detail = []

            for d in order_detail_set:
                # Calcular unit_min (cantidad mínima en unidad base)
                quantity_minimum_unit = calculate_minimum_unit(d.quantity_sold, d.unit, d.product)

                # Obtener store (ProductStore ID) y subStore (SubsidiaryStore ID)
                store_id = None
                sub_store_id = None
                if d.product_store:
                    store_id = d.product_store.id
                    if d.product_store.subsidiary_store:
                        sub_store_id = d.product_store.subsidiary_store.id

                # Buscar lotes relacionados con esta orden y producto
                batch_id = None
                batch_number = ''

                # Buscar en BillDetailBatch relacionados con la orden y el producto
                bill_detail_batch = BillDetailBatch.objects.filter(
                    order=order_obj,
                    product=d.product
                ).first()

                if bill_detail_batch:
                    batch_number = bill_detail_batch.batch_number or ''
                    # Buscar el Batch por batch_number si existe
                    if batch_number and d.product_store:
                        batch_obj = Batch.objects.filter(
                            batch_number=batch_number,
                            product_store=d.product_store
                        ).first()
                        if batch_obj:
                            batch_id = batch_obj.id
                        else:
                            # Si no se encuentra con product_store, buscar solo por batch_number
                            batch_obj = Batch.objects.filter(batch_number=batch_number).first()
                            if batch_obj:
                                batch_id = batch_obj.id

                new_row = {
                    'id': d.id,
                    'product_id': d.product.id,
                    'product_name': d.product.name,
                    'quantity': float(d.quantity_sold),
                    'price': float(d.price_unit),
                    'unit_id': d.unit.id,
                    'unit_name': d.unit.name,
                    'unit_min': float(quantity_minimum_unit),
                    'batch_id': batch_id,
                    'batch_number': batch_number,
                    'store': store_id,
                    'subStore': sub_store_id,
                }
                detail.append(new_row)

            # Obtener datos del cliente
            client_id = None
            client_name = ''
            client_address = ''
            client_addresses = []
            cod_unit_exe = ''

            if order_obj.client:
                client_id = order_obj.client.id
                client_name = order_obj.client.names

                # Obtener direcciones del cliente
                client_addresses_list = order_obj.client.clientaddress_set.all()

                for addr in client_addresses_list:
                    # Validar que el atributo existe antes de usarlo
                    address_type = getattr(addr, 'type_adress', None)

                    client_addresses.append({
                        'address': addr.address,
                        'type': address_type
                    })

                    # Solo verificar si el atributo existe
                    if address_type == 'P':  # Dirección principal
                        client_address = addr.address

                if not client_address and client_addresses_list:
                    client_address = client_addresses_list.first().address

                cod_unit_exe = order_obj.client.cod_siaf or ''

            return JsonResponse({
                'success': True,
                'order_id': order_obj.id,
                'transaction_payment_type': order_obj.way_to_pay_type,
                'type_document': order_obj.type_document,
                'observation': order_obj.observation or '',
                'order_buy': order_obj.order_buy or '',
                'n_contract': order_obj.client.cod_siaf if order_obj.client else '',
                'client_id': client_id,
                'client_name': client_name,
                'client_address': client_address,
                'client_addresses': client_addresses,
                'cod_unit_exe': cod_unit_exe,
                'detail': detail,
            }, status=HTTPStatus.OK)

        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'ID de orden inválido',
            }, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al obtener la orden: {str(e)}',
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def search_order_for_credit_note(request):
    if request.method == 'GET':
        query = request.GET.get('query', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        # Search by ID, or Serial, or Correlative
        orders = Order.objects.filter(
            (Q(id__icontains=query) if query.isdigit() else Q()) |
            Q(serial__icontains=query) |
            Q(correlative__icontains=query),
            subsidiary=subsidiary_obj,
            order_type='V'
        ).select_related('client').order_by('-id')[:10]

        results = []
        for o in orders:
            results.append({
                'id': o.id,
                'serial': o.serial,
                'correlative': o.correlative,
                'client_name': o.client.names if o.client else 'Cliente Público',
                'total': float(o.total),
                'date': o.create_at.strftime("%d/%m/%Y") if o.create_at else ''
            })

        return JsonResponse({'success': True, 'orders': results})

    else:
        return JsonResponse({
            'success': False,
            'message': 'Error de petición',
        }, status=HTTPStatus.BAD_REQUEST)


def get_order_details_ajax(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id', '')
        if not order_id:
            return JsonResponse({'success': False, 'message': 'ID de orden no proporcionado'})

        try:
            order_obj = Order.objects.select_related('client').get(id=int(order_id))
            order_details = order_obj.orderdetail_set.all().select_related('product', 'unit')

            details = []
            for d in order_details:
                # Get all presentation units for this product
                product_details = ProductDetail.objects.filter(product=d.product, is_enabled=True).select_related(
                    'unit')
                units = []
                current_factor = 1.0

                for pd in product_details:
                    units.append({
                        'id': pd.unit.id,
                        'name': pd.unit.name,
                        'factor': float(pd.quantity_minimum)
                    })
                    if pd.unit.id == d.unit.id:
                        current_factor = float(pd.quantity_minimum)

                details.append({
                    'id': d.id,
                    'product_name': d.product.name,
                    'product_id': d.product.id,
                    'unit_id': d.unit.id,
                    'unit_name': d.unit.name,
                    'quantity': float(d.quantity_sold),
                    'price_unit': float(d.price_unit),
                    'total': float(d.multiply()),
                    'current_factor': current_factor,
                    'units': units
                })

            return JsonResponse({
                'success': True,
                'client_name': order_obj.client.names if order_obj.client else 'Cliente Público',
                'serial': order_obj.serial,
                'correlative': order_obj.correlative,
                'details': details
            })
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Orden no encontrada'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


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
        bill_details_set = BillDetail.objects.filter(bill=bill_obj, status_quantity='C')
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
                'quantity': str(round(bd.quantity, 0)),
                'quantity_in_units': str(
                    quantity_in_units.quantize(decimal.Decimal('0'), rounding=decimal.ROUND_HALF_UP)),
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


@transaction.atomic
def save_detail_to_warehouse(request):
    try:
        if request.method == 'GET':
            purchase_request = request.GET.get('details', '')
            data_purchase = json.loads(purchase_request)

            assign_date = str(data_purchase["AssignDate"])
            bill_id = int(data_purchase["Bill"])
            bill_obj = Bill.objects.get(id=int(bill_id))
            guide_number = data_purchase["GuideNumber"]
            store = data_purchase["Store"]

            user_id = request.user.id
            user_obj = User.objects.get(id=user_id)
            subsidiary_obj = get_subsidiary_by_user(user_obj)
            subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(store))
            unit_und_obj = Unit.objects.get(name='UND')

            # Obtener purchase relacionado
            bill_purchase_set = BillPurchase.objects.filter(bill=bill_obj).first()
            purchase_obj = bill_purchase_set.purchase if bill_purchase_set else None

            # Resumen para devolver
            summary_data = {
                'products': [],
                'credit_notes': [],
                'orders': []
            }

            for d in data_purchase['Details']:
                product_id = int(d['Product'])
                product_obj = Product.objects.get(id=product_id)
                unit_id = int(d['UnitPurchase'])
                unit_obj = Unit.objects.get(id=unit_id)

                unit_min_product = ProductDetail.objects.get(product=product_obj, unit=unit_obj).quantity_minimum
                price_purchase = decimal.Decimal(d['PricePurchase'])
                price_purchase_unit = (price_purchase / unit_min_product) / decimal.Decimal(1.18)

                # Obtener o crear ProductStore
                try:
                    product_store_obj = ProductStore.objects.get(product=product_obj,
                                                                 subsidiary_store=subsidiary_store_obj)
                except ProductStore.DoesNotExist:
                    product_store_obj = ProductStore.objects.create(product=product_obj,
                                                                    subsidiary_store=subsidiary_store_obj,
                                                                    stock=0)

                # Calcular totales
                sum_quantity_entered_principal = decimal.Decimal(d['SumQuantityEnteredPrincipal'])
                sum_quantity_entered_units = decimal.Decimal(d['SumQuantityEnteredUnits'])
                sum_quantity_entered_total_in_units = (sum_quantity_entered_principal * unit_min_product) + sum_quantity_entered_units
                sum_quantity_entered_in_purchase_unit = sum_quantity_entered_principal + (sum_quantity_entered_units / unit_min_product)

                sum_quantity_returned_principal = decimal.Decimal(d.get('SumQuantityReturnedPrincipal', 0) or 0)
                sum_quantity_returned_units = decimal.Decimal(d.get('SumQuantityReturnedUnits', 0) or 0)
                sum_quantity_returned_total_in_units = (sum_quantity_returned_principal * unit_min_product) + sum_quantity_returned_units
                sum_quantity_returned_in_purchase_unit = sum_quantity_returned_principal + (sum_quantity_returned_units / unit_min_product)

                sum_quantity_sold_principal = decimal.Decimal(d.get('SumQuantitySoldPrincipal', 0) or 0)
                sum_quantity_sold_units = decimal.Decimal(d.get('SumQuantitySoldUnits', 0) or 0)
                sum_quantity_sold_total_in_units = (sum_quantity_sold_principal * unit_min_product) + sum_quantity_sold_units
                sum_quantity_sold_in_purchase_unit = sum_quantity_sold_principal + (sum_quantity_sold_units / unit_min_product)

                # Datos del producto para el resumen
                product_summary = {
                    'product_name': product_obj.name,
                    'product_id': product_id,
                    'batches': []
                }

                # ----------------------------------- SIEMPRE REGISTRAR ENTRADA EN KARDEX --------------------------------------------------
                if sum_quantity_entered_total_in_units > 0:
                    # Guardar quantity y unit como el usuario ingresó: si usó cajas → cajas, si usó UND → UND
                    if sum_quantity_entered_principal > 0:
                        qty_entered_billdetail = sum_quantity_entered_principal
                        unit_entered_billdetail = unit_obj
                    else:
                        qty_entered_billdetail = sum_quantity_entered_units
                        unit_entered_billdetail = unit_und_obj

                    detail_entered_obj = BillDetail.objects.create(
                        quantity=qty_entered_billdetail,
                        unit=unit_entered_billdetail,
                        price_unit=price_purchase,
                        product=product_obj,
                        status_quantity='I',
                        bill=bill_obj
                    )

                    # Registrar en kardex (entrada)
                    has_kardex = Kardex.objects.filter(product_store_id=product_store_obj.id).exists()
                    if not has_kardex:
                        new_total_stock = product_store_obj.stock + sum_quantity_entered_total_in_units
                        product_store_obj.stock = new_total_stock
                        product_store_obj.save()
                        kardex_obj = kardex_initial(
                            product_store_obj,
                            new_total_stock,
                            price_purchase_unit,
                            bill_detail_obj=detail_entered_obj
                        )
                    else:
                        total_cost = sum_quantity_entered_total_in_units * price_purchase_unit
                        kardex_obj = kardex_input(
                            product_store_obj.id,
                            sum_quantity_entered_total_in_units,
                            total_cost,
                            type_document='01',
                            type_operation='02',
                            bill_detail_obj=detail_entered_obj
                        )

                    # Procesar cada batch
                    for b in d.get('Batch', []):
                        batch_number = b.get('batchNumber', '')
                        batch_expiration = b.get('batchExpiration', '')
                        entered_quantity_principal = decimal.Decimal(b.get('EnteredQuantityPrincipal', 0) or 0)
                        entered_quantity_units = decimal.Decimal(b.get('EnteredQuantityUnits', 0) or 0)
                        entered_quantity_total_in_units = (entered_quantity_principal * unit_min_product) + entered_quantity_units

                        if entered_quantity_total_in_units > 0 and batch_number:
                            # Crear Batch
                            batch_set = Batch.objects.filter(batch_number=str(batch_number), product_store=product_store_obj)
                            batch_quantity_remaining = batch_set.last().remaining_quantity if batch_set.exists() else 0

                            batch_obj = Batch.objects.create(
                                expiration_date=batch_expiration,
                                batch_number=batch_number,
                                kardex=kardex_obj,
                                quantity=entered_quantity_total_in_units,
                                remaining_quantity=entered_quantity_total_in_units + batch_quantity_remaining,
                                product_store=product_store_obj
                            )

                            # Crear BillDetailBatch
                            BillDetailBatch.objects.create(
                                batch_number=batch_number,
                                batch_expiration_date=batch_expiration,
                                product=product_obj,
                                quantity=entered_quantity_total_in_units,
                                unit=unit_und_obj,
                                bill_detail=detail_entered_obj
                            )

                            # Datos del lote para el resumen
                            batch_summary = {
                                'batch_number': batch_number,
                                'batch_expiration': batch_expiration,
                                'entered_quantity': float(entered_quantity_total_in_units),
                                'returned_quantity': 0,
                                'sold_quantity': 0,
                                'credit_note_id': None,
                                'order_id': None
                            }

                            # ----------------------------------- DEVOLUCIÓN: CREAR CREDIT NOTE PRIMERO, LUEGO KARDEX OUTPUT --------------------------------------------------
                            returned_quantity_principal = decimal.Decimal(b.get('ReturnedQuantityPrincipal', 0) or 0)
                            returned_quantity_units = decimal.Decimal(b.get('ReturnedQuantityUnits', 0) or 0)
                            returned_quantity_total_in_units = (returned_quantity_principal * unit_min_product) + returned_quantity_units

                            if returned_quantity_total_in_units > 0:
                                # Validar que existe batch con cantidad suficiente
                                if batch_obj.remaining_quantity < returned_quantity_total_in_units:
                                    return JsonResponse({
                                        'error': f'No hay suficiente cantidad en el lote {batch_number} para devolver {returned_quantity_total_in_units} unidades del producto {product_obj.name}. Cantidad disponible: {batch_obj.remaining_quantity}',
                                    }, status=HTTPStatus.BAD_REQUEST)

                                # Crear BillDetail para devolución: quantity y unit como el usuario ingresó
                                sum_quantity_returned_in_purchase_unit = returned_quantity_principal + (returned_quantity_units / unit_min_product)
                                if returned_quantity_principal > 0:
                                    qty_returned_billdetail = returned_quantity_principal
                                    unit_returned_billdetail = unit_obj
                                else:
                                    qty_returned_billdetail = returned_quantity_units
                                    unit_returned_billdetail = unit_und_obj

                                detail_returned_obj = BillDetail.objects.create(
                                    quantity=qty_returned_billdetail,
                                    unit=unit_returned_billdetail,
                                    price_unit=price_purchase,
                                    product=product_obj,
                                    status_quantity='D',
                                    bill=bill_obj
                                )

                                # Crear CreditNote y CreditNoteDetail PRIMERO
                                credit_note_obj = CreditNote.objects.create(
                                    credit_note_serial='PENDIENTE_NC',
                                    credit_note_number='000000',
                                    issue_date=datetime.now().date(),
                                    bill=bill_obj,
                                    purchase=purchase_obj,
                                    status='P',
                                    motive=f'Devolución de mercadería - Lote: {batch_number}'
                                )

                                # Calcular total para CreditNoteDetail (valor monetario)
                                returned_total = returned_quantity_total_in_units * price_purchase_unit

                                # price_unit para CreditNoteDetail: según la unidad usada por el usuario
                                if unit_returned_billdetail == unit_und_obj:
                                    price_returned_display = price_purchase / unit_min_product
                                else:
                                    price_returned_display = price_purchase

                                credit_note_detail_obj = CreditNoteDetail.objects.create(
                                    credit_note=credit_note_obj,
                                    product=product_obj,
                                    quantity=qty_returned_billdetail,
                                    unit=unit_returned_billdetail,
                                    price_unit=price_returned_display,
                                    total=returned_total,
                                    code=product_obj.code or '',
                                    description=product_obj.name
                                )

                                # Registrar salida en kardex DESPUÉS de crear CreditNoteDetail
                                kardex_ouput(
                                    product_store_obj.id,
                                    returned_quantity_total_in_units,
                                    type_document='07',  # NOTA DE CREDITO
                                    type_operation='06',  # DEVOLUCION ENTREGADA
                                    credit_note_detail_obj=credit_note_detail_obj,
                                    batch_obj=batch_obj
                                )

                                # Actualizar batch_obj después de la devolución
                                batch_obj.refresh_from_db()
                                # Obtener el batch más reciente después de kardex_ouput
                                current_batch = Batch.objects.filter(
                                    batch_number=str(batch_number),
                                    product_store=product_store_obj
                                ).order_by('-id').first()
                                batch_obj = current_batch if current_batch else batch_obj

                                # Crear BillDetailBatch para devolución
                                BillDetailBatch.objects.create(
                                    batch_number=batch_number,
                                    batch_expiration_date=batch_expiration,
                                    product=product_obj,
                                    quantity=returned_quantity_total_in_units,
                                    unit=unit_und_obj,
                                    bill_detail=detail_returned_obj
                                )

                                batch_summary['returned_quantity'] = float(returned_quantity_total_in_units)
                                batch_summary['credit_note_id'] = credit_note_obj.id
                                summary_data['credit_notes'].append({
                                    'id': credit_note_obj.id,
                                    'serial': credit_note_obj.credit_note_serial,
                                    'number': credit_note_obj.credit_note_number,
                                    'product': product_obj.name
                                })

                            # ----------------------------------- VENTA: CREAR ORDER PRIMERO, LUEGO KARDEX OUTPUT --------------------------------------------------
                            sold_quantity_principal = decimal.Decimal(b.get('SoldQuantityPrincipal', 0) or 0)
                            sold_quantity_units = decimal.Decimal(b.get('SoldQuantityUnit', 0) or 0)
                            sold_quantity_total_in_units = (sold_quantity_principal * unit_min_product) + sold_quantity_units

                            if sold_quantity_total_in_units > 0:
                                # Obtener el batch más reciente (después de devolución si hubo)
                                current_batch = Batch.objects.filter(
                                    batch_number=str(batch_number),
                                    product_store=product_store_obj
                                ).order_by('-id').first()

                                if not current_batch:
                                    return JsonResponse({
                                        'error': f'No se encontró el lote {batch_number} para el producto {product_obj.name}',
                                    }, status=HTTPStatus.BAD_REQUEST)

                                if current_batch.remaining_quantity < sold_quantity_total_in_units:
                                    return JsonResponse({
                                        'error': f'No hay suficiente cantidad en el lote {batch_number} para vender {sold_quantity_total_in_units} unidades del producto {product_obj.name}. Cantidad disponible: {current_batch.remaining_quantity}',
                                    }, status=HTTPStatus.BAD_REQUEST)

                                # Crear BillDetail para venta: quantity y unit como el usuario ingresó
                                sum_quantity_sold_in_purchase_unit = sold_quantity_principal + (sold_quantity_units / unit_min_product)
                                if sold_quantity_principal > 0:
                                    qty_sold_billdetail = sold_quantity_principal
                                    unit_sold_billdetail = unit_obj
                                else:
                                    qty_sold_billdetail = sold_quantity_units
                                    unit_sold_billdetail = unit_und_obj

                                detail_sold_obj = BillDetail.objects.create(
                                    quantity=qty_sold_billdetail,
                                    unit=unit_sold_billdetail,
                                    price_unit=price_purchase,
                                    product=product_obj,
                                    status_quantity='V',
                                    bill=bill_obj
                                )

                                # Crear Order y OrderDetail PRIMERO
                                create_date = utc_to_local(datetime.now())
                                order_obj = Order.objects.create(
                                    order_type='V',
                                    status='P',
                                    sale_type='VA',
                                    subsidiary=subsidiary_obj,
                                    create_at=create_date,
                                    user=user_obj,
                                    correlative='000000',
                                    serial='PENDIENTE_CE'
                                )

                                # Obtener precio de venta según la unidad que ingresó el usuario
                                if unit_sold_billdetail == unit_und_obj:
                                    product_detail_sale = ProductDetail.objects.filter(product=product_obj, unit=unit_und_obj).first()
                                    if product_detail_sale:
                                        price_sale = product_detail_sale.price_sale
                                    else:
                                        product_detail_sale = ProductDetail.objects.filter(product=product_obj, unit=unit_obj).first()
                                        price_sale = (product_detail_sale.price_sale / unit_min_product) if product_detail_sale else price_purchase / unit_min_product
                                else:
                                    product_detail_sale = ProductDetail.objects.filter(product=product_obj, unit=unit_obj).first()
                                    price_sale = product_detail_sale.price_sale if product_detail_sale else price_purchase

                                order_detail_obj = OrderDetail.objects.create(
                                    order=order_obj,
                                    product=product_obj,
                                    quantity_sold=qty_sold_billdetail,
                                    unit=unit_sold_billdetail,
                                    price_unit=price_sale,
                                    status='P',
                                    product_store=product_store_obj,
                                    commentary=f'Venta desde almacén - Lote: {batch_number}'
                                )

                                # Actualizar total del order
                                order_obj.total = order_detail_obj.multiply()
                                order_obj.save()

                                # Registrar salida en kardex DESPUÉS de crear OrderDetail
                                kardex_ouput(
                                    product_store_obj.id,
                                    sold_quantity_total_in_units,
                                    type_document='00',  # OTROS
                                    type_operation='01',  # VENTA
                                    order_detail_obj=order_detail_obj,
                                    batch_obj=current_batch
                                )

                                # Crear BillDetailBatch para venta
                                BillDetailBatch.objects.create(
                                    batch_number=batch_number,
                                    batch_expiration_date=batch_expiration,
                                    product=product_obj,
                                    quantity=sold_quantity_total_in_units,
                                    unit=unit_und_obj,
                                    bill_detail=detail_sold_obj,
                                    order=order_obj
                                )

                                batch_summary['sold_quantity'] = float(sold_quantity_total_in_units)
                                batch_summary['order_id'] = order_obj.id
                                summary_data['orders'].append({
                                    'id': order_obj.id,
                                    'serial': order_obj.serial,
                                    'correlative': order_obj.correlative,
                                    'product': product_obj.name
                                })

                            product_summary['batches'].append(batch_summary)

                if product_summary['batches']:
                    summary_data['products'].append(product_summary)

            # Actualizar bill_obj después de procesar todos los detalles
            bill_obj.guide_number = guide_number
            bill_obj.assign_date = assign_date
            bill_obj.store_destiny = subsidiary_store_obj
            bill_obj.status = 'E'
            bill_obj.save()

            # Actualizar purchases relacionadas
            bill_purchase_set = BillPurchase.objects.filter(bill=bill_obj)
            for bp in bill_purchase_set:
                purchase_obj = bp.purchase
                purchase_obj.status = 'A'
                purchase_obj.save()

            # Formatear fechas para el resumen
            from datetime import datetime as dt
            try:
                assign_date_formatted = dt.strptime(assign_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                assign_date_formatted = assign_date
            
            # Formatear fechas de lotes en el resumen
            for product in summary_data['products']:
                for batch in product['batches']:
                    if batch.get('batch_expiration'):
                        try:
                            batch['batch_expiration'] = dt.strptime(batch['batch_expiration'], '%Y-%m-%d').strftime('%d/%m/%Y')
                        except:
                            pass

            # Renderizar template de resumen
            t = loader.get_template('sales/assignment_summary.html')
            c = {
                'summary_data': summary_data,
                'bill_obj': bill_obj,
                'assign_date': assign_date_formatted,
                'guide_number': guide_number,
                'store_name': subsidiary_store_obj.name,
                'subsidiary_name': subsidiary_store_obj.subsidiary.name if subsidiary_store_obj.subsidiary else ''
            }

            return JsonResponse({
                'message': 'Productos Registrados Correctamente',
                'success': True,
                'summary_html': t.render(c, request)
            }, status=HTTPStatus.OK)
    except Exception as e:
        import traceback
        error_message = f"Contacte con sistema para corregir el sgt error: {str(e)}"
        error_traceback = traceback.format_exc()
        print(f"Error en save_detail_to_warehouse: {error_traceback}")

        return JsonResponse({
            'error': error_message,
            'detail': str(e)
        }, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def get_details_by_bill(request):
    if request.method == 'GET':
        bill_id = request.GET.get('bill_id', '')
        bill_obj = Bill.objects.get(pk=int(bill_id))
        details_bill = BillDetail.objects.filter(bill=bill_obj)

        # Pre-calcular cantidades por producto y unidad para optimizar
        quantities_cache = {}
        unit_reference_cache = {}
        
        # Primero, determinar la unidad de referencia para cada producto
        for d in details_bill:
            cache_key_product = f"{d.product.id}"
            if cache_key_product not in unit_reference_cache:
                bill_detail_comprado = BillDetail.objects.filter(
                    bill=bill_obj, 
                    product=d.product, 
                    status_quantity='C'
                ).first()
                
                if not bill_detail_comprado:
                    unit_reference = d.unit
                else:
                    unit_reference = bill_detail_comprado.unit
                
                unit_reference_cache[cache_key_product] = unit_reference
        
        # Calcular cantidades para cada producto único
        products_processed = set()
        for d in details_bill:
            unit_reference = unit_reference_cache.get(f"{d.product.id}", d.unit)
            cache_key = f"{d.product.id}_{unit_reference.id}"
            
            if cache_key not in products_processed:
                products_processed.add(cache_key)
                
                # Obtener quantity_minimum para la conversión a UND
                quantity_minimum = decimal.Decimal('1')
                try:
                    product_detail = ProductDetail.objects.get(
                        product=d.product, 
                        unit=unit_reference
                    )
                    quantity_minimum = product_detail.quantity_minimum
                except ProductDetail.DoesNotExist:
                    quantity_minimum = decimal.Decimal('1')
                
                # Calcular cantidades totales por estado para este producto y unidad
                quantity_entered = BillDetail.objects.filter(
                    bill=bill_obj,
                    product=d.product,
                    unit=unit_reference,
                    status_quantity='I'
                ).aggregate(total=Sum('quantity'))['total'] or decimal.Decimal('0')
                
                quantity_returned = BillDetail.objects.filter(
                    bill=bill_obj,
                    product=d.product,
                    unit=unit_reference,
                    status_quantity='D'
                ).aggregate(total=Sum('quantity'))['total'] or decimal.Decimal('0')
                
                quantity_sold = BillDetail.objects.filter(
                    bill=bill_obj,
                    product=d.product,
                    unit=unit_reference,
                    status_quantity='V'
                ).aggregate(total=Sum('quantity'))['total'] or decimal.Decimal('0')
                
                # Calcular equivalencias en UND
                quantity_entered_und = quantity_entered * quantity_minimum
                quantity_returned_und = quantity_returned * quantity_minimum
                quantity_sold_und = quantity_sold * quantity_minimum
                
                quantities_cache[cache_key] = {
                    'quantity_entered': quantity_entered,
                    'quantity_returned': quantity_returned,
                    'quantity_sold': quantity_sold,
                    'quantity_entered_und': quantity_entered_und,
                    'quantity_returned_und': quantity_returned_und,
                    'quantity_sold_und': quantity_sold_und,
                    'unit_reference': unit_reference.description,
                }

        details_dict = []
        for d in details_bill:

            store = ''
            credit_number = ''
            bill_applied = 'Sin Aplicar'

            # if d.order:
            #     order_number = d.order.id
            #     order_number_bill = d.order.serial + '-' + d.order.correlative
            if d.kardex_set.all():
                store = d.kardex_set.last().product_store.subsidiary_store.name

            credit_note_set = CreditNote.objects.filter(bill_note=d.bill)
            if credit_note_set.exists():
                credit_note_obj = credit_note_set.last()
                credit_number = f"{credit_note_obj.credit_note_serial}-{credit_note_obj.credit_note_number}"
                if credit_note_obj.bill is not None:
                    bill_applied = credit_note_obj.bill

            # Usar quantity y unit tal como se guardó en BillDetail (lo que ingresó el usuario)
            quantity_minimum = decimal.Decimal('1')
            try:
                product_detail = ProductDetail.objects.get(
                    product=d.product,
                    unit=d.unit
                )
                quantity_minimum = product_detail.quantity_minimum
            except ProductDetail.DoesNotExist:
                quantity_minimum = decimal.Decimal('1')

            quantity_display = d.quantity
            quantity_und_display = d.quantity * quantity_minimum
            # Mostrar conversión a UND solo cuando la unidad no es UND (ej. cajas)
            show_conversion_und = (d.unit.name != 'UND')

            item = {
                'id': d.id,
                'product': d.product.name,
                'quantity': d.quantity,
                'unit': d.unit.description,
                'price_unit': d.price_unit,
                'status_quantity': d.status_quantity,
                'status_display': d.get_status_quantity_display(),
                'store': store,
                'batch_number': '',
                'batch_expiration': '',
                'credit_note': credit_number,
                'bill_applied': bill_applied,
                'rowspan': d.billdetailbatch_set.count(),
                'details_batch': [],
                'quantity_display': str(round(quantity_display, 2)),
                'quantity_und_display': quantity_und_display,
                'unit_reference': d.unit.description,
                'show_conversion_und': show_conversion_und,
            }
            for b in d.billdetailbatch_set.all():
                order_number = ''
                order_number_bill = ''
                if b.order:
                    order_number = b.order.id
                    if b.order.serial is not None:
                        order_number_bill = b.order.serial + '-' + b.order.correlative
                
                # Calcular equivalencia en UND para el batch
                batch_quantity_minimum = decimal.Decimal('1')
                try:
                    batch_product_detail = ProductDetail.objects.get(
                        product=b.product, 
                        unit=b.unit
                    )
                    batch_quantity_minimum = batch_product_detail.quantity_minimum
                except ProductDetail.DoesNotExist:
                    batch_quantity_minimum = decimal.Decimal('1')
                
                batch_quantity_und = b.quantity * batch_quantity_minimum
                
                item_batch = {
                    'id': b.id,
                    'batch_number': b.batch_number,
                    'batch_expiration': b.batch_expiration_date,
                    'batch_quantity': b.quantity,
                    'batch_unit': b.unit.description,
                    'batch_quantity_und': batch_quantity_und,
                    'order_number': order_number,
                    'order_number_bill': order_number_bill,
                }
                item.get('details_batch').append(item_batch)
            details_dict.append(item)
        # print(details_dict)
        t = loader.get_template('sales/details_bill.html')
        c = ({
            'details_dict': details_dict,
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


def credit_note_order_list(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        credit_note_order_set = CreditNoteOrder.objects.filter(order__subsidiary=subsidiary_obj).order_by('-id')

        return render(request, 'sales/credit_note_order_list.html', {
            'credit_note_order_set': credit_note_order_set,
        })


def modal_credit_note_order(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id', '')
        order_obj = None
        order_detail_set = []

        if order_id and order_id.isdigit():
            order_obj = Order.objects.get(id=int(order_id))
            order_detail_set = order_obj.orderdetail_set.all()

        my_date = datetime.now()
        date_now = my_date.strftime("%Y-%m-%d")

        # Get orders for the initial search dropdown (optional, can also use AJAX)
        subsidiary_obj = get_subsidiary_by_user(request.user)

        t = loader.get_template('sales/modal_credit_note_order.html')
        c = ({
            'order_obj': order_obj,
            'order_detail_set': order_detail_set,
            'date': date_now,
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def view_credit_note_order_detail(request):
    """View to display credit note order details in a modal"""
    if request.method == 'GET':
        credit_note_id = request.GET.get('credit_note_id', '')

        try:
            credit_note = CreditNoteOrder.objects.select_related('order', 'order__client').get(id=int(credit_note_id))
            details = credit_note.creditnoteorderdetail_set.select_related('product', 'unit').all()

            # Calculate totals
            total = credit_note.get_total()
            subtotal = total / decimal.Decimal('1.18')
            igv = total - subtotal

            t = loader.get_template('sales/modal_credit_note_order_detail.html')
            c = {
                'credit_note': credit_note,
                'details': details,
                'total': total,
                'subtotal': subtotal,
                'igv': igv,
            }

            return JsonResponse({
                'html': t.render(c, request),
            })
        except CreditNoteOrder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Nota de crédito no encontrada'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al cargar el detalle: {str(e)}'
            }, status=500)

    return JsonResponse({'message': 'Método no permitido'}, status=400)


@csrf_exempt
def save_credit_note_order(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                order_id = request.POST.get('order_id', '')
                credit_serial = request.POST.get('credit_note_serial', '')  # Corrected
                credit_number = request.POST.get('credit_note_number', '')  # Corrected
                issue_date = request.POST.get('issue_date', '')  # Corrected
                motive = request.POST.get('motive', '')  # Corrected
                details_json = request.POST.get('details', '[]')
                details = json.loads(details_json)

                order_obj = Order.objects.get(id=int(order_id))

                credit_note_order = CreditNoteOrder.objects.create(
                    credit_note_serial=credit_serial,
                    credit_note_number=credit_number,
                    issue_date=issue_date,
                    order=order_obj,
                    motive=motive,
                    status='E'
                )

                for d in details:
                    order_detail_id = d.get('order_detail_id')
                    quantity_returned = decimal.Decimal(d.get('quantity'))
                    unit_id = d.get('unit_id')  # New: Unit from detail
                    price_unit = decimal.Decimal(d.get('price_unit'))  # New: Price from detail

                    if quantity_returned <= 0:
                        continue

                    order_detail_obj = OrderDetail.objects.get(id=int(order_detail_id))
                    unit_obj = Unit.objects.get(id=int(unit_id)) if unit_id else order_detail_obj.unit

                    # Calculate total for the detail
                    total_detail = quantity_returned * price_unit

                    credit_note_detail = CreditNoteOrderDetail.objects.create(
                        credit_note_order=credit_note_order,
                        product=order_detail_obj.product,
                        unit=unit_obj,
                        quantity=quantity_returned,
                        price_unit=price_unit,
                        total=total_detail,
                        description=order_detail_obj.product.name
                    )

                    # Kardex Integration
                    # Find the source batch from the original sale's kardex
                    kardex_sale = Kardex.objects.filter(order_detail=order_detail_obj, operation='S').last()

                    product_store = order_detail_obj.product_store

                    # Convert quantity to minimum units
                    quantity_minimum = calculate_minimum_unit(quantity_returned, unit_obj, order_detail_obj.product)

                    # Determine cost for kardex. We use the original price_unit from the Kardex Sale record if available
                    # otherwise we use the order detail price (approximated)
                    price_unit_cost = order_detail_obj.price_unit
                    if kardex_sale:
                        price_unit_cost = kardex_sale.price_unit

                    total_cost_kardex = quantity_minimum * price_unit_cost

                    # Call kardex_input with type_document='07' and type_operation='05'
                    kardex_input_obj = kardex_input(
                        product_store_id=product_store.id,
                        quantity=quantity_minimum,
                        total_cost=total_cost_kardex,
                        order_detail_obj=order_detail_obj,
                        type_document='07',
                        type_operation='05',
                        credit_note_order_detail_obj=credit_note_detail
                    )

                    # Update the batch - traceability requirement
                    if kardex_sale:
                        batch_movement = Batch.objects.filter(kardex=kardex_sale).last()
                        if batch_movement:
                            # Use same batch number and expiration date
                            latest_batch_record = Batch.objects.filter(
                                product_store=product_store,
                                batch_number=batch_movement.batch_number
                            ).order_by('-id').first()

                            Batch.objects.create(
                                batch_number=batch_movement.batch_number,
                                expiration_date=batch_movement.expiration_date,
                                quantity=quantity_minimum,
                                remaining_quantity=(
                                                       latest_batch_record.remaining_quantity if latest_batch_record else 0) + quantity_minimum,
                                kardex=kardex_input_obj,
                                product_store=product_store
                            )

                            # Also update the most recent record's remaining_quantity to maintain consistency
                            if latest_batch_record:
                                latest_batch_record.remaining_quantity += quantity_minimum
                                latest_batch_record.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Nota de Crédito registrada con éxito',
                    'credit_note_id': credit_note_order.id
                }, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al guardar la nota de crédito: {str(e)}'
            }, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


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
        guide_detail_dict = []
        total = 0
        subsidiary_store_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj, category='V')
        for gd in guide_detail_set:
            product_store_get = ProductStore.objects.get(product=gd.product, subsidiary_store=subsidiary_store_obj)
            price_sale = gd.guide.contract_detail.contractdetailitem_set.last().price_unit
            product_detail_get = ProductDetail.objects.get(product=gd.product, unit=gd.unit)
            # price_purchase = product_detail_get.price_purchase
            # price_sale = product_detail_get.price_sale

            quantity_minimum = product_detail_get.quantity_minimum
            sub_total = round(price_sale * gd.quantity, 2)

            # Obtener todas las unidades disponibles para este producto
            product_units = Unit.objects.filter(productdetail__product=gd.product)

            # Obtener todos los lotes asociados a este detalle de guía desde GuideDetailBatch
            batch_details = gd.batch_details.all()  # related_name='batch_details'

            # Si hay lotes en GuideDetailBatch, agruparlos por producto
            if batch_details.exists():
                # La cantidad total es la de la guía, no la suma de los lotes
                total_quantity = gd.quantity
                total_subtotal = price_sale * gd.quantity

                # Crear lista de números de lote separados por comas
                batch_numbers = [batch_detail.batch.batch_number for batch_detail in batch_details]
                batch_numbers_str = ', '.join(batch_numbers)

                # Crear lista de IDs de lote para el atributo batch
                batch_ids = [str(batch_detail.batch.id) for batch_detail in batch_details]
                batch_ids_str = ', '.join(batch_ids)

                item_guide = {
                    'id': gd.id,
                    'quantity': str(round(total_quantity, 2)),
                    'product_id': gd.product.id,
                    'product_name': gd.product.name,
                    'unit_id': gd.unit.id,
                    'unit': gd.unit.name,
                    'product_units': [(unit.id, unit.name) for unit in product_units],
                    # 'price_purchase': price_purchase,
                    'price_sale': str(round(price_sale, 2)),
                    'subtotal': str(round(total_subtotal, 2)),
                    'quantity_minimum': str(quantity_minimum),
                    'store_product': product_store_get.id,
                    'stock': product_store_get.stock,
                    'batch_id': batch_ids_str,
                    'batch_number': batch_numbers_str
                }
                total += total_subtotal
                guide_detail_dict.append(item_guide)
            else:
                # Fallback al comportamiento original si no hay lotes en GuideDetailBatch
                item_guide = {
                    'id': gd.id,
                    'quantity': str(round(gd.quantity, 2)),
                    'product_id': gd.product.id,
                    'product_name': gd.product.name,
                    'unit_id': gd.unit.id,
                    'unit': gd.unit.name,
                    'product_units': [(unit.id, unit.name) for unit in product_units],
                    # 'price_purchase': price_purchase,
                    'price_sale': str(round(price_sale, 2)),
                    'subtotal': str(sub_total),
                    'quantity_minimum': str(quantity_minimum),
                    'store_product': product_store_get.id,
                    'stock': product_store_get.stock,
                    'batch_id': gd.batch.id if gd.batch else '',
                    'batch_number': gd.batch.batch_number if gd.batch else '-'
                }
                total += sub_total
                guide_detail_dict.append(item_guide)

        if subsidiary_obj is None:
            error = "No tiene una Sede o Almacen para vender"
        else:
            sales_store = SubsidiaryStore.objects.filter(
                subsidiary=subsidiary_obj, category='V').first()
        return render(request, 'sales/sales_list.html', {
            'choices_payments': [(k, v) for k, v in TransactionPayment._meta.get_field('type').choices
                                 if k not in ['EC', 'L', 'Y']],
            'date': formatdate,
            'document_types': DocumentType.objects.all(),
            'error': error,
            'sales_store': sales_store,
            'choices_account': cash_set,
            'choices_account_bank': cash_deposit_set,
            'guide_obj': guide_obj,
            'subsidiary_obj': subsidiary_obj,
            'guide_detail_set': guide_detail_set,
            'guide_detail_dict': guide_detail_dict,
            'series': SubsidiarySerial.objects.filter(subsidiary=subsidiary_obj),
            'order_set': Order._meta.get_field('order_type').choices,
            'users': User.objects.filter(is_superuser=False, is_staff=True),
            'total': str(round(total, 2))
        })
    return JsonResponse({'message': 'Error actualice o contacte con sistemas.'}, status=HTTPStatus.BAD_REQUEST)


from decimal import Decimal, ROUND_HALF_UP

QTY_0 = Decimal("0.00")


def q2(x):
    return (x or Decimal("0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def q4(x):
    return (x or Decimal("0")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def absd(x):
    return abs(x or Decimal("0"))


def kardex_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    subsidiaries = Subsidiary.objects.all()
    subsidiaries_stores = SubsidiaryStore.objects.all()

    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        return render(request, 'sales/new_kardex_list.html', {
            'formatdate': formatdate,
            'product_set': Product.objects.filter(is_enabled=True).order_by('id'),
            'subsidiaries': subsidiaries,
            'subsidiaries_stores': subsidiaries_stores,
        })

    if request.method != 'POST':
        return JsonResponse({'message': 'Error actualice o contacte con sistemas.'}, status=HTTPStatus.BAD_REQUEST)

    product_id = request.POST.get('product')
    subsidiary_id = request.POST.get('subsidiary')
    subsidiary_store = request.POST.get('subsidiary_store')

    product_store_qs = ProductStore.objects.filter(product_id=product_id, subsidiary_store_id=subsidiary_store)
    if not product_store_qs.exists():
        data = {'error': "El Producto no cuenta con kardex en el Almacen Seleccionado"}
        return JsonResponse(data, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    product_store_obj = product_store_qs.last()

    kardex_qs = (Kardex.objects
                 .filter(product_store=product_store_obj)
                 .select_related(
        'product_store',
        'order_detail__order',
        'guide_detail',
        'bill_detail__bill',
        'credit_note_detail__credit_note'
    )
                 .order_by('create_at', 'id')
                 )

    saldo_qty = Decimal("0")
    saldo_unit = Decimal("0")
    saldo_total = Decimal("0")

    kardex_dict = []

    # Sumas de totales columnas
    sum_quantities_entries = Decimal("0")
    sum_total_cost_entries = Decimal("0")
    sum_quantities_exits = Decimal("0")
    sum_total_cost_exits = Decimal("0")

    sum_saldo_qty = Decimal("0")
    sum_saldo_unit = Decimal("0")
    sum_saldo_total = Decimal("0")

    # Sumas para resumen
    purchase_units = Decimal("0")
    purchase_valorized = Decimal("0")

    initial_units = Decimal("0")
    initial_valorized = Decimal("0")

    # 1. Separar iniciales para que aparezcan siempre al inicio (operation 'C')
    initial_qs = kardex_qs.filter(operation='C').order_by('create_at', 'id')
    other_qs = kardex_qs.exclude(operation='C').order_by('create_at', 'id')

    for k in initial_qs:
        qty = k.remaining_quantity or Decimal("0")
        price_unit = k.remaining_price or Decimal("0")
        price_total = k.remaining_price_total or (qty * price_unit)

        saldo_qty += qty
        saldo_total += price_total
        if saldo_qty != 0:
            saldo_unit = (saldo_total / saldo_qty).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        else:
            saldo_unit = price_unit

        initial_units += qty
        initial_valorized += price_total

        item = {
            'id': k.id,
            'operation': 'C',
            'period': k.create_at.strftime("%Y-%m") if k.create_at else "",
            'date': k.create_at.strftime("%d/%m/%Y") if k.create_at else "",
            'type_document': k.type_document,
            'serial': '',
            'number': '',
            'type_operation': k.type_operation,
            'entry_qty': Decimal("0"),
            'entry_unit': Decimal("0"),
            'entry_total': Decimal("0"),
            'exit_qty': Decimal("0"),
            'exit_unit': Decimal("0"),
            'exit_total': Decimal("0"),
            'remaining_quantity': q2(saldo_qty),
            'remaining_price': q4(saldo_unit),
            'remaining_price_total': saldo_total,
        }
        kardex_dict.append(item)

        sum_saldo_qty += saldo_qty
        sum_saldo_unit += saldo_unit
        sum_saldo_total += saldo_total

    # 2. Procesar el resto de operaciones
    for k in other_qs:
        qty = k.quantity or Decimal("0")
        price_unit = k.price_unit or Decimal("0")
        price_total = k.price_total or (qty * price_unit)

        # Notas de credito especiales
        # NC Compra: operation 'S', type_doc '07', type_op '06' -> Columna Entradas Negativo
        is_nc_purchase = (k.operation == 'S' and k.type_document == '07' and k.type_operation == '06')
        # NC Venta: operation 'E', type_doc '07', type_op '05' -> Columna Salidas Negativo
        is_nc_sale = (k.operation == 'E' and k.type_document == '07' and k.type_operation == '05')

        entry_qty = Decimal("0")
        entry_unit = Decimal("0")
        entry_total = Decimal("0")

        exit_qty = Decimal("0")
        exit_unit = Decimal("0")
        exit_total = Decimal("0")

        if is_nc_purchase:
            entry_qty = -qty
            entry_total = -price_total
            entry_unit = price_unit

            saldo_qty += entry_qty  # resta del saldo
            saldo_total += entry_total
            if saldo_qty != 0:
                saldo_unit = (saldo_total / saldo_qty).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            # Se resta de compras para el cuadro resumen
            purchase_units += entry_qty
            purchase_valorized += entry_total

        elif is_nc_sale:
            exit_qty = -qty
            exit_total = -price_total
            exit_unit = price_unit

            saldo_qty -= exit_qty  # suma al saldo
            saldo_total -= exit_total
            if saldo_qty != 0:
                saldo_unit = (saldo_total / saldo_qty).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        elif k.operation == 'E':
            entry_qty = qty
            entry_unit = price_unit
            entry_total = price_total

            saldo_qty += entry_qty
            saldo_total += entry_total
            if saldo_qty != 0:
                saldo_unit = (saldo_total / saldo_qty).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            if k.type_document in ['01', '03']:
                purchase_units += entry_qty
                purchase_valorized += entry_total

        elif k.operation == 'S':
            exit_qty = qty
            exit_unit = saldo_unit  # Costo promedio anterior
            exit_total = exit_qty * exit_unit

            saldo_qty -= exit_qty
            saldo_total -= exit_total

        serial = ''
        number = ''
        if k.bill_detail and k.bill_detail.bill:
            serial = k.bill_detail.bill.serial
            number = k.bill_detail.bill.correlative
        elif k.order_detail and k.order_detail.order:
            serial = k.order_detail.order.serial
            number = k.order_detail.order.correlative
        elif k.credit_note_detail and k.credit_note_detail.credit_note:
            serial = k.credit_note_detail.credit_note.credit_note_serial
            number = k.credit_note_detail.credit_note.credit_note_number

        item = {
            'id': k.id,
            'operation': k.operation,
            'period': k.create_at.strftime("%Y-%m") if k.create_at else "",
            'date': k.create_at.strftime("%d/%m/%Y") if k.create_at else "",
            'type_document': k.type_document,
            'serial': serial,
            'number': str(number).zfill(7) if number != '' else '',
            'type_operation': k.type_operation,
            'entry_qty': q2(entry_qty),
            'entry_unit': q4(entry_unit),
            'entry_total': entry_total,
            'exit_qty': q2(exit_qty),
            'exit_unit': q4(exit_unit),
            'exit_total': exit_total,
            'remaining_quantity': q2(saldo_qty),
            'remaining_price': q4(saldo_unit),
            'remaining_price_total': saldo_total,
        }
        kardex_dict.append(item)

        sum_quantities_entries += entry_qty
        sum_total_cost_entries += entry_total
        sum_quantities_exits += exit_qty
        sum_total_cost_exits += exit_total

        sum_saldo_qty += saldo_qty
        sum_saldo_unit += saldo_unit
        sum_saldo_total += saldo_total

    summary = {
        'initial_units': initial_units,
        'initial_valorized': initial_valorized,
        'purchase_units': purchase_units,
        'purchase_valorized': purchase_valorized,
        'final_units': saldo_qty,
        'final_valorized': saldo_total,
        'cost_sales_units': initial_units + purchase_units - saldo_qty,
        'cost_sales_valorized': initial_valorized + purchase_valorized - saldo_total
    }

    tpl = loader.get_template('sales/new_kardex_grid_list.html')

    context = {
        'product_id': product_id,
        'kardex_dict': kardex_dict,
        'sum_quantities_entries': sum_quantities_entries,
        'sum_total_cost_entries': sum_total_cost_entries,
        'sum_quantities_exits': sum_quantities_exits,
        'sum_total_cost_exits': sum_total_cost_exits,
        'sum_saldo_qty': sum_saldo_qty,
        'sum_saldo_unit': sum_saldo_unit,
        'sum_saldo_total': sum_saldo_total,
        'summary': summary
    }

    return JsonResponse({'grid': tpl.render(context, request)}, status=HTTPStatus.OK)


def get_product_autocomplete(request):
    if request.method == 'GET':
        search = request.GET.get('search')
        product = []
        if search:
            product_set = Product.objects.filter(name__icontains=search, is_enabled=True).order_by('id')
            for c in product_set:
                product.append({
                    'id': c.id,
                    'code': c.code,
                    'names': c.name,
                    'brand': c.product_brand.name,
                    'weight': c.weight,
                })
        return JsonResponse({
            'status': True,
            'product': product
        })


def get_product_by_id(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_set = None
        product_id = request.GET.get('productId', '')

        if product_id != '':
            product_set = Product.objects.filter(id=product_id).select_related(
                'product_family', 'product_brand'
            ).prefetch_related(
                Prefetch(
                    'productstore_set',
                    queryset=ProductStore.objects.select_related('subsidiary_store__subsidiary')
                        .annotate(
                        is_primary_store=Case(
                            When(subsidiary_store__subsidiary=subsidiary_obj.id, then=Value(0)),
                            default=Value(1),
                            output_field=IntegerField()
                        )
                    )
                        .order_by('is_primary_store', 'id')
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


def modal_batch(request):
    if request.method == 'GET':
        ps_id = request.GET.get('ps', '')
        product_store_obj = ProductStore.objects.get(id=int(ps_id))
        # batch_set = Batch.objects.filter(product_store__id=int(ps_id)).order_by('id')
        # last_batches = Batch.objects.filter(
        #     batch_number=OuterRef('batch_number'),
        #     product_store__id=int(ps_id)
        # ).order_by('-create_at')
        #
        # latest_batches = Batch.objects.filter(
        #     product_store__id=int(ps_id)
        # ).annotate(last_create_at=Subquery(last_batches.values('create_at')[:1])).filter(create_at=F('last_create_at'))

        last_batches = Batch.objects.filter(
            batch_number=OuterRef('batch_number'), product_store__id=int(ps_id)).order_by('-id')

        latest_batches = Batch.objects.filter(
            product_store__id=int(ps_id)
        ).annotate(last_id=Subquery(last_batches.values('id')[:1])).filter(id=F('last_id'), remaining_quantity__gt=0)

        if latest_batches.exists():
            product_obj = product_store_obj.product
            tpl = loader.get_template('sales/modal_batch.html')
            context = ({
                'batch_set': latest_batches,
                'product_obj': product_obj,
                'product_store_obj': product_store_obj,
                'product_detail_set': ProductDetail.objects.filter(product=product_obj)
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
            }, status=HTTPStatus.OK)

        else:
            return JsonResponse({
                'success': False,
                'message': 'El Producto no cuenta con Lotes en la sucursal. Revisar el Producto'
            }, status=HTTPStatus.OK)


def check_batch_number(request):
    """
    Verifica si el número de lote ya existe en la BD para un producto en un almacén.
    No pueden haber dos lotes con el mismo número para el mismo producto en el mismo almacén.
    Returns: flag=True si el lote ya existe (duplicado), flag=False si no existe (válido).
    """
    if request.method == 'GET':
        flag = False
        number_batch = str(request.GET.get('number_batch', '')).strip()
        subsidiary_store = request.GET.get('subsidiary_store', '')
        product_id = request.GET.get('product_id', '')

        if number_batch and subsidiary_store and product_id:
            try:
                subsidiary_store_id = int(subsidiary_store)
                product_id_int = int(product_id)
                # Filtrar por: mismo número de lote, mismo producto y mismo almacén
                batch_set = Batch.objects.filter(
                    batch_number=number_batch,
                    product_store__subsidiary_store_id=subsidiary_store_id,
                    product_store__product_id=product_id_int
                )
                if batch_set.exists():
                    flag = True
            except (ValueError, TypeError):
                pass

        return JsonResponse({
            'flag': flag
        }, status=HTTPStatus.OK)


def sales_report_professional(request):
    """
    Reporte de ventas profesional y minimalista para órdenes con tipo de documento Boleta (B) o Factura (F)
    """
    from django.db.models import Sum, Count, Avg
    from django.utils import timezone
    from datetime import datetime, timedelta
    import json

    # Parámetros de filtro
    today = timezone.now().date()
    start_date = request.GET.get('start_date', today.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    subsidiary_id = request.GET.get('subsidiary', '')
    client_id = request.GET.get('client', '')

    # Filtro base para órdenes con tipo de documento B (Boleta) o F (Factura)
    orders = Order.objects.filter(type_document__in=['B', 'F'])

    # Aplicar filtros adicionales
    if start_date:
        orders = orders.filter(create_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(create_at__date__lte=end_date)
    if subsidiary_id:
        orders = orders.filter(subsidiary_id=subsidiary_id)
    if client_id:
        orders = orders.filter(client_id=client_id)

    # Obtener datos para filtros
    from apps.hrm.models import Subsidiary

    subsidiaries = Subsidiary.objects.all()
    clients = Client.objects.all()

    # Contexto para la plantilla
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'subsidiary_id': subsidiary_id,
        'client_id': client_id,
        'orders': orders.order_by('-create_at')[:100],  # Últimas 100 órdenes
        'subsidiaries': subsidiaries,
        'clients': clients,
    }

    return render(request, 'sales/sales_report_professional.html', context)


def accounts_receivable_report(request):
    """
    Reporte profesional de cuentas por cobrar
    """
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    if request.method == 'GET':
        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        # Obtener clientes para el filtro
        clients = Client.objects.filter(
            order__isnull=False,
            order__subsidiary=subsidiary_obj,
        ).distinct('id').values('id', 'names').order_by('id', 'names')

        return render(request, 'sales/accounts_receivable_report.html', {
            'formatdate': formatdate,
            'clients': clients,
        })

    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        client_id = request.POST.get('client_id', '')
        payment_status = request.POST.get('payment_status', 'all')  # all, pending, paid

        # Determinar el filtro de estado de pago
        if payment_status == 'paid':
            # Solo órdenes completamente pagadas
            status_pay_filter = 'C'
        elif payment_status == 'pending':
            # Solo órdenes con pagos pendientes
            status_pay_filter = 'P'
        elif payment_status == 'without_warranty':
            # Pagos sin garantía verificada
            status_pay_filter = None  # Se filtrará después por garantía
        else:
            # Todas las órdenes (P y C)
            status_pay_filter = None

        # Obtener órdenes según el filtro de estado de pago
        if status_pay_filter is not None:
            # Filtrar por un estado específico de pago
            orders_query = Order.objects.filter(
                subsidiary=subsidiary_obj,
                order_type='V',
                status__in=['P', 'C'],  # Estado de la orden (Pendiente o Completado)
                status_pay=status_pay_filter  # Estado del pago
            )
        else:
            # Traer todas las órdenes (tanto pendientes como completadas)
            orders_query = Order.objects.filter(
                subsidiary=subsidiary_obj,
                order_type='V',
                status__in=['P', 'C'],  # Estado de la orden (Pendiente o Completado)
                status_pay__in=['P', 'C']  # Todas las órdenes de pago
            )

        if client_id:
            orders_query = orders_query.filter(client_id=client_id)

        if start_date and end_date:
            orders_query = orders_query.filter(create_at__date__range=[start_date, end_date])

        # Filtrar por garantía si es necesario
        if payment_status == 'without_warranty':
            orders_query = orders_query.filter(
                total_warranty__gt=0,
                pay_day_warranty__isnull=True
            )

        orders_data = []

        for order in orders_query:
            # Calcular total de la orden
            # order_total = get_total_order(order.id)
            order_total = order.total

            # Calcular pagos realizados
            loan_payments = LoanPayment.objects.filter(
                order_id=order.id,
                type='V'
            )
            # Calcular garantias realizados
            loan_payments_warranties = LoanPayment.objects.filter(
                order_id=order.id,
                type='G'
            )

            total_paid = sum([lp.pay for lp in loan_payments]) if loan_payments.exists() else decimal.Decimal('0.00')
            total_warranties = sum(
                [lp.pay for lp in loan_payments_warranties]) if loan_payments_warranties.exists() else decimal.Decimal(
                '0.00')
            pending_amount = order_total - (total_paid + order.total_retention + order.total_warranty)
            pending_warranty = decimal.Decimal(order.total_warranty) - decimal.Decimal(total_warranties)

            # Obtener detalles de pagos de factura (type='V')
            payment_details = []
            for lp in loan_payments:
                transaction_payments = TransactionPayment.objects.filter(loan_payment=lp)
                for tp in transaction_payments:
                    file_url = lp.file.url if lp.file and lp.file.name != 'img/image_placeholder.jpg' else None
                    payment_details.append({
                        'date': lp.operation_date if lp.operation_date else lp.create_at.date(),
                        'amount': tp.payment,
                        'type': tp.get_type_display(),
                        'operation_code': tp.operation_code if tp.operation_code else '-',
                        'file': file_url,
                        'loan_payment_id': lp.id
                    })

            # Obtener detalles de pagos de garantía (type='G')
            warranty_details = []
            for lp in loan_payments_warranties:
                transaction_payments = TransactionPayment.objects.filter(loan_payment=lp)
                for tp in transaction_payments:
                    file_url = lp.file.url if lp.file and lp.file.name != 'img/image_placeholder.jpg' else None
                    warranty_details.append({
                        'date': lp.operation_date if lp.operation_date else lp.create_at.date(),
                        'amount': tp.payment,
                        'type': tp.get_type_display(),
                        'operation_code': tp.operation_code if tp.operation_code else '-',
                        'file': file_url,
                        'loan_payment_id': lp.id
                    })

            # Verificar si la orden tiene las tres fases
            has_all_phases = order.phase_c and order.phase_d and order.phase_g

            # Verificar si la orden está completamente pagada (factura + garantía si existe)
            is_paid = pending_amount == 0
            is_warranty_complete = pending_warranty <= 0 if order.total_warranty > 0 else True
            is_complete = is_paid and is_warranty_complete
            # print("bill", order.serial + order.correlative)
            # print("is_warranty_complete", is_warranty_complete)
            # print("pending_warranty", pending_warranty)
            # print("-------------")
            # Actualizar el status de la orden en la base de datos
            if is_complete:
                if order.status != 'C':
                    order.status = 'C'
                    order.save(update_fields=['status'])
                if order.status_pay != 'C':
                    order.status_pay = 'C'
                    order.save(update_fields=['status_pay'])
            else:
                if order.status == 'C' and not is_complete:
                    order.status = 'P'
                    order.save(update_fields=['status'])
                if is_paid and order.status_pay != 'C':
                    order.status_pay = 'C'
                    order.save(update_fields=['status_pay'])
                elif not is_paid and order.status_pay != 'P':
                    order.status_pay = 'P'
                    order.save(update_fields=['status_pay'])

            orders_data.append({
                'order_id': order.id,
                'order_date': order.create_at,
                'order_total': order_total,
                'total_paid': total_paid,
                'total_payed': order.total_payed if order.total_payed else decimal.Decimal('0.00'),
                # Total pagado del modelo
                'total_retention': order.total_retention if order.total_retention else decimal.Decimal('0.00'),
                'total_warranty': order.total_warranty if order.total_warranty else decimal.Decimal('0.00'),
                'total_warranties_paid': total_warranties,
                'pay_day_warranty': order.pay_day_warranty,
                'pending_amount': pending_amount,
                'pending_warranty': str(pending_warranty),
                'payment_details': payment_details,
                'warranty_details': warranty_details,
                'correlative': order.correlative if order.correlative else '-',
                'serial': order.serial if order.serial else '-',
                'document': f"{order.serial or ''}-{order.correlative or ''}",
                'type_document': order.get_type_document_display() if order.type_document else 'SIN DOCUMENTO',
                'client_id': order.client.id if order.client else 0,
                'client_name': order.client.names if order.client else 'SIN CLIENTE',
                'is_paid': is_paid,
                'is_warranty_complete': is_warranty_complete,
                'is_complete': is_complete,
                'has_all_phases': has_all_phases,
                'phase_c': order.phase_c,
                'phase_d': order.phase_d,
                'phase_g': order.phase_g,
            })

        # Ordenar por fecha descendente
        orders_data.sort(key=lambda x: x['order_date'])

        # Calcular totales
        total_debt = sum([order['order_total'] for order in orders_data])
        total_paid = sum([order['total_paid'] for order in orders_data])  # Pagos de factura (type='V')
        total_payed = sum([order['total_payed'] for order in orders_data])
        total_retention = sum([order['total_retention'] for order in orders_data])
        # total_warranty = sum([order['total_warranty'] for order in orders_data])  # Monto total de garantía
        total_warranties_paid = sum(
            [order['total_warranties_paid'] for order in orders_data])  # Garantías pagadas (type='G')
        total_pending = sum([order['pending_amount'] for order in orders_data])
        total_orders = len(orders_data)

        tpl = loader.get_template('sales/accounts_receivable_grid.html')
        context = {
            'orders_data': orders_data,
            'start_date': start_date,
            'end_date': end_date,
            'payment_status': payment_status,
            'total_debt': total_debt,
            'total_paid': total_paid,
            'total_payed': total_payed,
            'total_retention': total_retention,
            # 'total_warranty': total_warranty,
            'total_warranties_paid': total_warranties_paid,
            'total_pending': total_pending,
            'total_orders': total_orders
        }
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_client_payment_modal(request):
    """
    Obtener modal para agregar pago de cliente
    """
    if request.method == 'GET':
        order_id = request.GET.get('order_id')
        client_id = request.GET.get('client_id')

        order = Order.objects.get(id=order_id)
        client = Client.objects.get(id=client_id)

        # Calcular total pendiente
        order_total = get_total_order(order.id)
        loan_payments = LoanPayment.objects.filter(order_id=order.id, type='V')
        total_paid = sum([lp.pay for lp in loan_payments]) if loan_payments.exists() else decimal.Decimal('0.00')
        # El saldo por verificar es la diferencia entre el total y lo que está registrado en total_payed
        # pending_amount = order_total - (order.total_payed if order.total_payed else decimal.Decimal('0.00'))

        # Obtener cuentas de caja disponibles
        cash_accounts = Cash.objects.filter(
            accounting_account__code__startswith='104'
        )

        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        # Calcular monto pendiente
        print(order_total)
        print(total_paid)
        print(order.total_retention)
        print(order.total_warranty)
        pending_amount = order_total - (total_paid + order.total_retention + order.total_warranty)
        print(pending_amount)

        # Verificar si la orden tiene las tres fases
        has_all_phases = order.phase_c and order.phase_d and order.phase_g

        tpl = loader.get_template('sales/client_payment_modal.html')
        context = {
            'order': order,
            'client': client,
            'order_total': '{:,}'.format(round(order_total, 2)),
            'total_paid': total_paid,
            'total_payed': '{:,}'.format(round(order.total_payed, 2)),
            'total_warranty': '{:,}'.format(round(order.total_warranty, 2)),
            'total_retention': '{:,}'.format(round(order.total_retention, 2)),
            'pending_amount': str(pending_amount),
            'has_all_phases': has_all_phases,
            'cash_accounts': cash_accounts,
            'payment_types': TransactionPayment._meta.get_field('type').choices,
            'formatdate': formatdate,
        }

        return JsonResponse({
            'modal': tpl.render(context, request),
        }, status=HTTPStatus.OK)


@csrf_exempt
def save_client_payment(request):
    """
    Guardar pago de cliente
    """
    if request.method == 'POST':
        try:
            order_id = request.POST.get('order_id')
            client_id = request.POST.get('client_id')
            payment_amount = decimal.Decimal(request.POST.get('payment_amount'))
            payment_type = request.POST.get('payment_type')
            operation_code = request.POST.get('operation_code', '')
            cash_account_id = request.POST.get('cash_account_id')
            operation_date = request.POST.get('operation_date')
            observation = request.POST.get('observation', '')

            # Obtener objetos
            order = Order.objects.get(id=order_id)
            client = Client.objects.get(id=client_id)
            cash_account = Cash.objects.get(id=cash_account_id) if cash_account_id else None

            # Subir archivo si se proporciona
            payment_file = None
            if 'payment_file' in request.FILES:
                payment_file = request.FILES['payment_file']

            # Crear LoanPayment con archivo
            loan_payment = LoanPayment.objects.create(
                pay=payment_amount,
                order_detail=order.orderdetail_set.first(),  # Usar el primer OrderDetail
                type='V',  # Venta
                operation_date=operation_date,
                observation=observation,
                order=order,
                file=payment_file if payment_file else 'img/image_placeholder.jpg'
            )

            # Crear TransactionPayment
            transaction_payment = TransactionPayment.objects.create(
                payment=payment_amount,
                type=payment_type,
                operation_code=operation_code,
                loan_payment=loan_payment
            )

            # Crear CashFlow si es necesario
            if cash_account:
                cash_flow = CashFlow.objects.create(
                    transaction_date=operation_date,
                    description=f"Pago cliente: {client.names} - Orden: {order.correlative or order.id}",
                    type='E',  # Entrada
                    total=payment_amount,
                    cash=cash_account,
                    operation_code=operation_code,
                    order=order,
                    user=request.user,
                    client=client
                )

            # Actualizar total_payed en la orden
            order_total = get_total_order(order.id)
            all_payments = LoanPayment.objects.filter(order_id=order.id, type='V')
            total_paid = sum([lp.pay for lp in all_payments])

            # Actualizar total_payed (este es el campo que se verifica)
            order.total_payed = total_paid

            # Verificar si la orden está completamente pagada
            if total_paid >= order_total:
                order.status_pay = 'C'  # Completado
            else:
                order.status_pay = 'P'  # Pendiente

            order.save()

            return JsonResponse({
                'success': True,
                'message': 'Pago registrado exitosamente'
            }, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al registrar pago: {str(e)}'
            }, status=HTTPStatus.BAD_REQUEST)


def get_warranty_verification_modal(request):
    """
    Obtener modal para verificar garantía
    """
    if request.method == 'GET':
        order_id = request.GET.get('order_id')
        client_id = request.GET.get('client_id')

        order = Order.objects.get(id=order_id)
        client = Client.objects.get(id=client_id)

        mydate = datetime.now()
        formatdate = mydate.strftime("%Y-%m-%d")

        tpl = loader.get_template('sales/warranty_verification_modal.html')

        cash_accounts = Cash.objects.filter(
            accounting_account__code__startswith='104'
        )

        # Verificar si la orden tiene las tres fases
        has_all_phases = order.phase_c and order.phase_d and order.phase_g

        context = {
            'order': order,
            'total_warranty': '{:,}'.format(round(order.total_warranty, 2)),
            'client': client,
            'formatdate': formatdate,
            'has_all_phases': has_all_phases,
            'cash_accounts': cash_accounts,
            'payment_types': TransactionPayment._meta.get_field('type').choices,
        }

        return JsonResponse({
            'modal': tpl.render(context, request),
        }, status=HTTPStatus.OK)


@csrf_exempt
def save_warranty_verification(request):
    """
    Guardar verificación de garantía
    """
    if request.method == 'POST':
        try:
            order_id = request.POST.get('order_id')
            client_id = request.POST.get('client_id')
            warranty_payment_date = request.POST.get('warranty_payment_date')
            warranty_operation_code = request.POST.get('warranty_operation_code', '')
            warranty_observation = request.POST.get('warranty_observation', '')
            warranty_payment_type = request.POST.get('warranty_payment_type', '')
            cash_account_id = request.POST.get('warranty_cash_account_id')

            order = Order.objects.get(id=order_id)
            client = Client.objects.get(id=client_id)
            cash_account = Cash.objects.get(id=cash_account_id) if cash_account_id else None

            # Guardar archivo si se proporciona
            warranty_file = None
            if 'warranty_file' in request.FILES:
                warranty_file = request.FILES['warranty_file']

            loan_payment = LoanPayment.objects.create(
                pay=order.total_warranty,
                order_detail=order.orderdetail_set.first(),  # Usar el primer OrderDetail
                type='G',  # Garantia
                operation_date=warranty_payment_date,
                observation=warranty_observation,
                order=order,
                file=warranty_file if warranty_file else 'img/image_placeholder.jpg'
            )

            TransactionPayment.objects.create(
                payment=order.total_warranty,
                type=warranty_payment_type,
                operation_code=warranty_operation_code,
                loan_payment=loan_payment
            )

            if cash_account:
                CashFlow.objects.create(
                    transaction_date=warranty_payment_date,
                    description=f"Garantia de la Factura: {order.serial}-{order.correlative or order.id}",
                    type='E',  # Entrada
                    total=order.total_warranty,
                    cash=cash_account,
                    operation_code=warranty_operation_code,
                    order=order,
                    user=request.user,
                    client=client
                )

            order.status = 'C'
            order.save()

            return JsonResponse({
                'success': True,
                'message': 'Garantía verificada exitosamente'
            }, status=HTTPStatus.OK)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al verificar garantía: {str(e)}'
            }, status=HTTPStatus.BAD_REQUEST)


def get_payment_details_modal(request):
    """
    Obtener modal para ver todos los pagos de una orden
    """
    if request.method == 'GET':
        order_id = request.GET.get('order_id')
        client_id = request.GET.get('client_id')

        order = Order.objects.get(id=order_id)
        client = Client.objects.get(id=client_id)

        # Obtener todos los pagos
        loan_payments = LoanPayment.objects.filter(order_id=order.id, type='V').order_by('-create_at')
        payments_list = []
        for lp in loan_payments:
            transaction_payments = TransactionPayment.objects.filter(loan_payment=lp)
            for tp in transaction_payments:
                file_url = lp.file.url if lp.file and lp.file.name != 'img/image_placeholder.jpg' else None
                payments_list.append({
                    'date': lp.operation_date if lp.operation_date else lp.create_at.date(),
                    'amount': tp.payment,
                    'type': tp.get_type_display(),
                    'operation_code': tp.operation_code if tp.operation_code else '-',
                    'file': file_url,
                    'loan_payment_id': lp.id,
                    'observation': lp.observation or ''
                })

        tpl = loader.get_template('sales/payment_details_view_modal.html')
        context = {
            'order': order,
            'client': client,
            'payments_list': payments_list,
        }

        return JsonResponse({
            'modal': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_warranty_details_modal(request):
    """
    Obtener modal para ver detalles de garantía
    """
    if request.method == 'GET':
        order_id = request.GET.get('order_id')
        client_id = request.GET.get('client_id')

        order = Order.objects.get(id=order_id)
        client = Client.objects.get(id=client_id)

        tpl = loader.get_template('sales/warranty_details_view_modal.html')
        context = {
            'order': order,
            'client': client,
        }

        return JsonResponse({
            'modal': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_payment_detail_view(request):
    """
    Obtener vista detallada de un pago específico (factura o garantía)
    """
    if request.method == 'GET':
        loan_payment_id = request.GET.get('loan_payment_id')
        order_id = request.GET.get('order_id')
        client_id = request.GET.get('client_id')

        order = Order.objects.get(id=order_id)
        client = Client.objects.get(id=client_id) if client_id else order.client

        # Obtener el pago específico
        loan_payment = LoanPayment.objects.get(id=loan_payment_id)
        payment_type = loan_payment.type  # 'V' para factura, 'G' para garantía

        # Obtener dirección principal del cliente
        main_address = client.clientaddress_set.filter(type_address='P').first()
        client_address = None
        if main_address:
            address_parts = []
            if main_address.address:
                address_parts.append(main_address.address)
            if main_address.district:
                address_parts.append(str(main_address.district))
            if main_address.province:
                address_parts.append(str(main_address.province))
            if main_address.department:
                address_parts.append(str(main_address.department))
            client_address = ', '.join(address_parts) if address_parts else None

        # Obtener transacciones del pago
        transaction_payments = TransactionPayment.objects.filter(loan_payment=loan_payment)
        file_url = loan_payment.file.url if loan_payment.file and loan_payment.file.name != 'img/image_placeholder.jpg' else None

        payment_data = {
            'loan_payment': loan_payment,
            'transaction_payments': transaction_payments,
            'file_url': file_url,
            'date': loan_payment.operation_date if loan_payment.operation_date else loan_payment.create_at.date(),
            'amount': '{:,}'.format(round(loan_payment.pay, 2)),
            'observation': loan_payment.observation or ''
        }

        tpl = loader.get_template('sales/payment_detail_view_modal.html')
        context = {
            'order': order,
            'client': client,
            'client_address': client_address,
            'payment_data': payment_data,
            'payment_type': payment_type,  # 'V' o 'G'
            'is_warranty': payment_type == 'G',
        }

        return JsonResponse({
            'modal': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_order_by_correlative(request):
    if request.method == 'GET':
        correlative = request.GET.get('correlative', '')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        order_set = Order.objects.filter(subsidiary_store__subsidiary=subsidiary_obj, correlative=int(correlative),
                                         order_type='T')
        if order_set.exists():
            order_obj = order_set.last()
            type_document = order_obj.client.clienttype_set.last().document_type.id
            document_number = order_obj.client.clienttype_set.last().document_number
            client_name = order_obj.client.names
            validity_date = order_obj.validity_date
            date_completion = order_obj.date_completion
            place_delivery = order_obj.place_delivery
            type_quotation = order_obj.type_quotation
            type_name_quotation = order_obj.type_name_quotation
            transaction_payment_type = order_obj.way_to_pay_type
            observation = order_obj.observation
            correlative = order_obj.correlative_sale
            order_detail_set = OrderDetail.objects.filter(order=order_obj)
            detail = []
            for d in order_detail_set:
                product_store_obj = d.product_store  # Use the product_store from OrderDetail
                quantity_minimum_unit = calculate_minimum_unit(d.quantity_sold, d.unit, d.product)
                stock = 0
                product_store_id = None

                if product_store_obj:
                    product_store_id = product_store_obj.id
                    stock = product_store_obj.stock

                new_row = {
                    'id': d.id,
                    'product_id': d.product.id,
                    'product_name': d.product.name,
                    'product_brand': d.product.product_brand.name,
                    'unit_id': d.unit.id,
                    'unit_name': d.unit.name,
                    'quantity': d.quantity_sold,
                    'price': d.price_unit,
                    'store': product_store_id,
                    'stock': round(stock, 0),
                    'unit_min': quantity_minimum_unit,
                }
                detail.append(new_row)

            return JsonResponse({
                'success': True,
                'order_id': order_obj.id,
                'document_type': type_document,
                'document_number': document_number,
                'client_name': client_name,
                'validity_date': validity_date,
                'date_completion': date_completion,
                'place_delivery': place_delivery,
                'type_quotation': type_quotation,
                'type_name_quotation': type_name_quotation,
                'observation': observation,
                'transaction_payment_type': transaction_payment_type,
                'correlative': correlative,
                'detail': detail,
            }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'success': False,
                'message': 'No se encontro la Cotización Numero: ' + str(correlative),
            }, status=HTTPStatus.OK)


# ==================== MÓDULO DE PRECIOS ====================

class PriceManagementView(View):
    """Vista unificada para gestión de precios"""
    model_price_type = PriceType
    model_product_price = ProductPrice
    form_class_price_type = FormPriceType
    form_class_product_price = FormProductPrice
    template_name = 'sales/price_management.html'

    def get_queryset_price_types(self):
        return self.model_price_type.objects.all().order_by('id')

    def get_queryset_product_prices(self):
        return self.model_product_price.objects.select_related('price_type', 'product_detail__product',
                                                               'product_detail__unit').all().order_by(
            'price_type__name', 'product_detail__product__name')

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['price_types'] = self.get_queryset_price_types()
        contexto['product_prices'] = self.get_queryset_product_prices()
        contexto['form_price_type'] = self.form_class_price_type
        contexto['form_product_price'] = self.form_class_product_price
        contexto['price_types_enabled'] = PriceType.objects.filter(is_enabled=True)
        contexto['product_details'] = ProductDetail.objects.filter(is_enabled=True).select_related('product',
                                                                                                   'unit').order_by(
            'product__name', 'unit__name')
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class PriceTypeList(View):
    """Vista legacy - redirige a la vista unificada"""

    def get(self, request, *args, **kwargs):
        return redirect('sales:price_management')


class ProductPriceList(View):
    """Vista legacy - redirige a la vista unificada"""

    def get(self, request, *args, **kwargs):
        return redirect('sales:price_management')


def price_type_save(request):
    if request.method == 'POST':
        try:
            price_type_id = request.POST.get('price_type_id', '')
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            is_enabled = request.POST.get('is_enabled', '') == 'on'

            if price_type_id:
                # Actualizar
                price_type_obj = PriceType.objects.get(id=int(price_type_id))
                price_type_obj.name = name
                price_type_obj.description = description
                price_type_obj.is_enabled = is_enabled
                price_type_obj.save()
                message = 'Tipo de precio actualizado correctamente'
            else:
                # Crear
                price_type_obj = PriceType.objects.create(
                    name=name,
                    description=description,
                    is_enabled=is_enabled
                )
                message = 'Tipo de precio creado correctamente'

            return JsonResponse({
                'success': True,
                'message': message,
                'price_type_id': price_type_obj.id
            }, status=HTTPStatus.OK)

        except IntegrityError:
            return JsonResponse({
                'success': False,
                'message': 'Ya existe un tipo de precio con este nombre o código'
            }, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=HTTPStatus.BAD_REQUEST)

    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def price_type_delete(request):
    if request.method == 'POST':
        try:
            price_type_id = request.POST.get('price_type_id', '')
            if price_type_id:
                price_type_obj = PriceType.objects.get(id=int(price_type_id))
                # Verificar si tiene precios asociados
                if price_type_obj.productprice_set.exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'No se puede eliminar porque tiene precios de productos asociados'
                    }, status=HTTPStatus.BAD_REQUEST)
                # Verificar si tiene clientes asociados
                if price_type_obj.client_set.exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'No se puede eliminar porque tiene clientes asociados'
                    }, status=HTTPStatus.BAD_REQUEST)
                price_type_obj.delete()
                return JsonResponse({
                    'success': True,
                    'message': 'Tipo de precio eliminado correctamente'
                }, status=HTTPStatus.OK)
        except PriceType.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Tipo de precio no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=HTTPStatus.BAD_REQUEST)

    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


class ProductPriceList(View):
    model = ProductPrice
    form_class = FormProductPrice
    template_name = 'sales/product_price_list.html'

    def get_queryset(self):
        return self.model.objects.select_related('price_type', 'product_detail__product',
                                                 'product_detail__unit').all().order_by('price_type__type',
                                                                                        'product_detail__product__name')

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['product_prices'] = self.get_queryset()
        contexto['form'] = self.form_class
        contexto['price_types'] = PriceType.objects.filter(is_enabled=True)
        contexto['product_details'] = ProductDetail.objects.filter(is_enabled=True).select_related('product', 'unit')
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


def product_price_save(request):
    if request.method == 'POST':
        try:
            product_price_id = request.POST.get('product_price_id', '')
            price_type_id = request.POST.get('price_type', '').strip()
            product_detail_id = request.POST.get('product_detail', '').strip()
            price = request.POST.get('price', '').strip()
            is_enabled = request.POST.get('is_enabled', '') == 'on'

            if not price_type_id or not product_detail_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Tipo de precio y producto son requeridos'
                }, status=HTTPStatus.BAD_REQUEST)

            # Si el precio es 0 o vacío, no guardar
            if not price or price == '' or decimal.Decimal(price) == 0:
                # Si existe un precio, eliminarlo
                if product_price_id:
                    try:
                        ProductPrice.objects.get(id=int(product_price_id)).delete()
                        return JsonResponse({
                            'success': True,
                            'message': 'Precio eliminado (precio en 0)',
                            'product_price_id': None
                        }, status=HTTPStatus.OK)
                    except ProductPrice.DoesNotExist:
                        pass
                return JsonResponse({
                    'success': True,
                    'message': 'Precio no guardado (precio en 0)',
                    'product_price_id': None
                }, status=HTTPStatus.OK)

            price_decimal = decimal.Decimal(price)

            if product_price_id:
                # Actualizar
                product_price_obj = ProductPrice.objects.get(id=int(product_price_id))
                product_price_obj.price = price_decimal
                product_price_obj.is_enabled = is_enabled
                product_price_obj.save()
                message = 'Precio actualizado correctamente'
            else:
                # Crear o actualizar si existe
                product_price_obj, created = ProductPrice.objects.update_or_create(
                    price_type_id=int(price_type_id),
                    product_detail_id=int(product_detail_id),
                    defaults={
                        'price': price_decimal,
                        'is_enabled': is_enabled
                    }
                )
                message = 'Precio guardado correctamente'

            return JsonResponse({
                'success': True,
                'message': message,
                'product_price_id': product_price_obj.id
            }, status=HTTPStatus.OK)

        except IntegrityError:
            return JsonResponse({
                'success': False,
                'message': 'Ya existe un precio para este tipo de precio y presentación'
            }, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=HTTPStatus.BAD_REQUEST)

    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def product_price_delete(request):
    if request.method == 'POST':
        try:
            product_price_id = request.POST.get('product_price_id', '')
            if product_price_id:
                product_price_obj = ProductPrice.objects.get(id=int(product_price_id))
                product_price_obj.delete()
                return JsonResponse({
                    'success': True,
                    'message': 'Precio de producto eliminado correctamente'
                }, status=HTTPStatus.OK)
        except ProductPrice.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Precio de producto no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=HTTPStatus.BAD_REQUEST)

    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def get_price_by_client_and_product(request):
    """Obtiene el precio de un producto según el tipo de precio del cliente"""
    if request.method == 'GET':
        try:
            client_id = request.GET.get('client_id', '')
            product_id = request.GET.get('product_id', '')
            unit_id = request.GET.get('unit_id', '')

            if not client_id or not product_id or not unit_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Faltan parámetros requeridos'
                }, status=HTTPStatus.BAD_REQUEST)

            client_obj = Client.objects.get(id=int(client_id))
            product_detail_obj = ProductDetail.objects.get(
                product_id=int(product_id),
                unit_id=int(unit_id)
            )

            # Si el cliente tiene un tipo de precio asignado
            if client_obj.price_type:
                try:
                    product_price_obj = ProductPrice.objects.get(
                        price_type=client_obj.price_type,
                        product_detail=product_detail_obj,
                        is_enabled=True
                    )
                    price = product_price_obj.price
                except ProductPrice.DoesNotExist:
                    # Si no existe precio específico, usar el precio de venta por defecto
                    price = product_detail_obj.price_sale
            else:
                # Si no tiene tipo de precio, usar el precio de venta por defecto
                price = product_detail_obj.price_sale

            return JsonResponse({
                'success': True,
                'price': float(price),
                'price_type': client_obj.price_type.name if client_obj.price_type else 'Precio por defecto'
            }, status=HTTPStatus.OK)

        except Client.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Cliente no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except ProductDetail.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Presentación de producto no encontrada'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=HTTPStatus.BAD_REQUEST)

    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)


def get_prices_by_price_type(request):
    """Obtiene todos los productos con sus precios para un tipo de precio específico"""
    if request.method == 'GET':
        try:
            price_type_id = request.GET.get('price_type_id', '')

            if not price_type_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Falta el parámetro price_type_id'
                }, status=HTTPStatus.BAD_REQUEST)

            price_type_obj = PriceType.objects.get(id=int(price_type_id))

            # Obtener todos los productos habilitados
            product_details = ProductDetail.objects.filter(is_enabled=True).select_related('product', 'unit').order_by(
                'product__name', 'unit__name')

            # Obtener precios existentes para este tipo de precio
            existing_prices = ProductPrice.objects.filter(
                price_type=price_type_obj
            ).select_related('product_detail__product', 'product_detail__unit')

            # Crear un diccionario de precios existentes por product_detail_id
            prices_dict = {pp.product_detail.id: {
                'id': pp.id,
                'price': float(pp.price),
                'is_enabled': pp.is_enabled
            } for pp in existing_prices}

            # Construir la lista con todos los productos
            products_list = []
            for pd in product_details:
                price_info = prices_dict.get(pd.id, None)
                products_list.append({
                    'product_detail_id': pd.id,
                    'product_id': pd.product.id,
                    'product_name': pd.product.name,
                    'unit_id': pd.unit.id,
                    'unit_name': pd.unit.name,
                    'price_id': price_info['id'] if price_info else None,
                    'price': price_info['price'] if price_info else 0.0,
                    'is_enabled': price_info['is_enabled'] if price_info else True,
                    'has_price': price_info is not None
                })

            return JsonResponse({
                'success': True,
                'price_type': price_type_obj.name,
                'price_type_id': price_type_obj.id,
                'products': products_list
            }, status=HTTPStatus.OK)

        except PriceType.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Tipo de precio no encontrado'
            }, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=HTTPStatus.BAD_REQUEST)

    return JsonResponse({'message': 'Error de petición.'}, status=HTTPStatus.BAD_REQUEST)