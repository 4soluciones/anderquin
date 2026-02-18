import decimal
from http import HTTPStatus
from django.db.models import Q, Max, F, Prefetch, OuterRef, Subquery, Value, IntegerField, Sum
from django.db.models.functions import Coalesce, Cast
from django.shortcuts import render
from django.views.generic import View, TemplateView, UpdateView, CreateView
from django.views.decorators.csrf import csrf_exempt
from .models import *
from apps.hrm.models import Subsidiary, Employee, District, Department, Province
from django.http import JsonResponse
from .forms import *
from django.urls import reverse_lazy
from apps.sales.models import Product, SubsidiaryStore, ProductStore, ProductDetail, ProductSubcategory, Unit, \
    ProductSupplier, TransactionPayment, Order, LoanPayment, ClientAddress, Batch
from apps.sales.views import kardex_ouput, kardex_input, kardex_initial, calculate_minimum_unit, Supplier
from apps.hrm.models import Subsidiary
import json
from django.db import DatabaseError, IntegrityError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import ImageFieldFile
from django.template import loader
from datetime import datetime
from django.db import DatabaseError, IntegrityError
from django.core import serializers
from datetime import date
# Create your views here.
from .. import sales
from ..buys.models import Purchase, ContractDetail, ContractDetailItem
from ..hrm.views import get_subsidiary_by_user
from ..sales.views_SUNAT import query_apis_net_dni_ruc


# ---------------------------------------Truck-----------------------------------
class TruckList(View):
    model = Truck
    form_class = FormTruck
    template_name = 'comercial/truck_list.html'

    def get_queryset(self):
        return self.model.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['trucks'] = self.get_queryset()  # agregamos la consulta al contexto
        contexto['driver_set'] = Driver.objects.all()
        contexto['form'] = self.form_class
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class TruckCreate(CreateView):
    model = Truck
    form_class = FormTruck
    template_name = 'comercial/truck_create.html'
    success_url = reverse_lazy('comercial:truck_list')

    def get_context_data(self, **kwargs):
        ctx = super(TruckCreate, self).get_context_data(**kwargs)
        ctx['brands'] = TruckBrand.objects.all()
        ctx['models'] = TruckModel.objects.all()
        return ctx


class TruckUpdate(UpdateView):
    model = Truck
    form_class = FormTruck
    template_name = 'comercial/truck_update.html'
    success_url = reverse_lazy('comercial:truck_list')

    def get_context_data(self, **kwargs):
        ctx = super(TruckUpdate, self).get_context_data(**kwargs)
        ctx['brands'] = TruckBrand.objects.all()
        ctx['models'] = TruckModel.objects.all()
        return ctx


# -------------------------------------- Towing -----------------------------------


class TowingList(View):
    model = Towing
    form_class = FormTowing
    template_name = 'comercial/towing_list.html'

    def get_queryset(self):
        return self.model.objects.all()

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['towings'] = self.get_queryset()  # agregamos la consulta al contexto
        contexto['form'] = self.form_class
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class TowingCreate(CreateView):
    model = Towing
    form_class = FormTowing
    template_name = 'comercial/towing_create.html'
    success_url = reverse_lazy('comercial:towing_list')

    def get_context_data(self, **kwargs):
        ctx = super(TowingCreate, self).get_context_data(**kwargs)
        ctx['brands'] = TowingBrand.objects.all()
        ctx['models'] = TowingModel.objects.all()
        return ctx


class TowingUpdate(UpdateView):
    model = Towing
    form_class = FormTowing
    template_name = 'comercial/towing_update.html'
    success_url = reverse_lazy('comercial:towing_list')

    def get_context_data(self, **kwargs):
        ctx = super(TowingUpdate, self).get_context_data(**kwargs)
        ctx['brands'] = TowingBrand.objects.all()
        ctx['models'] = TowingModel.objects.all()
        return ctx


# ----------------------------------------Guide------------------------------------


def new_guide(request, contract_detail=None):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    my_date = datetime.now()
    date_now = my_date.strftime("%Y-%m-%d")

    contract_detail_obj = None
    contract_detail_item_set = None
    contract_dict = []
    client = []
    weight_total = 0
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
            weight_total += decimal.Decimal(d.product.weight) * d.quantity
            item_contract = {
                'contract_detail_id': d.contract_detail.id,
                'id': d.id,
                'product_id': d.product.id,
                'product_name': d.product.name,
                'product_brand': d.product.product_brand.name,
                'quantity': d.quantity,
                'counter': counter,
                'weight': d.product.weight,
                'units': []
            }
            for pd in ProductDetail.objects.filter(product_id=d.product.id).all():
                item_units = {
                    'id': pd.id,
                    'unit_id': pd.unit.id,
                    'unit_name': pd.unit.name,
                    'unit_description': pd.unit.description,
                    'quantity_minimum': round(pd.quantity_minimum, 0),
                }
                item_contract.get('units').append(item_units)
            contract_dict.append(item_contract)
    supplier_obj = Supplier.objects.all()
    product_obj = Product.objects.all()
    my_date = datetime.now()
    formatdate = my_date.strftime("%Y-%m-%d")
    motive_set = GuideMotive.objects.filter(type='S', code__isnull=False).order_by('id')
    subsidiary_set = SubsidiaryStore.objects.filter(category='V').order_by('id')
    return render(request, 'comercial/guide.html', {
        'supplier_obj': supplier_obj,
        'product_obj': product_obj,
        # 'choices_payments': TransactionPayment._meta.get_field('type').choices,
        'choices_payments_purchase': Purchase._meta.get_field('payment_method').choices,
        'formatdate': formatdate,
        'supplier_set': Supplier.objects.all(),
        'client_set': Client.objects.all(),
        'subsidiary_store_set': SubsidiaryStore.objects.filter(category='V'),
        'subsidiary_set': json.dumps(list(subsidiary_set.values('id', 'name'))),
        'subsidiary_user': subsidiary_obj.id,
        'contract_detail_obj': contract_detail_obj,
        'client': json.dumps(client),
        'contract_detail_item_set': contract_detail_item_set,
        'contract_dict': contract_dict,
        'motive_set': motive_set,
        'date_now': date_now,
        'weight_total': str(round(weight_total / 1000, 2)),
    })


def modal_guide_origin(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        truck_set = Truck.objects.all()
        # pilot_set = Driver.objects.all()
        motive_set = GuideMotive.objects.filter(type='S')
        subsidiary_set = Subsidiary.objects.all().order_by('id', 'serial')
        t = loader.get_template('comercial/modal_guide_origin.html')
        c = ({
            'truck_set': truck_set,
            # 'pilot_set': pilot_set,
            'date': formatdate,
            'motive_set': motive_set,
            'department': Department.objects.all(),
            'province': Province.objects.all(),
            'district': District.objects.all(),
            'subsidiary_obj': subsidiary_obj,
            'subsidiary_set': subsidiary_set,
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


def modal_guide_destiny(request):
    if request.method == 'GET':
        client_id = request.GET.get('client')
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        client_obj = Client.objects.get(id=int(client_id))
        client_address_set = ClientAddress.objects.filter(client_id=client_id)
        truck_set = Truck.objects.all()
        # pilot_set = Driver.objects.all()
        motive_set = GuideMotive.objects.filter(type='S')
        district_set = District.objects.all()
        subsidiary_set = Subsidiary.objects.all()
        t = loader.get_template('comercial/modal_guide_destiny.html')
        c = ({
            'truck_set': truck_set,
            # 'pilot_set': pilot_set,
            'date': formatdate,
            'motive_set': motive_set,
            'subsidiary_obj': subsidiary_obj,
            'subsidiary_set': subsidiary_set,
            'department': Department.objects.all(),
            'province': Province.objects.all(),
            'district': District.objects.all(),
            'client_obj': client_obj,
            'client_address_set': client_address_set,
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


def save_new_address_client(request):
    if request.method == 'GET':
        client_id = request.GET.get('client_id')
        # department_destiny = request.GET.get('department_destiny')
        # province_destiny = request.GET.get('province_destiny')
        district_destiny = request.GET.get('district_destiny')
        new_address = request.GET.get('new_address')
        if client_id and district_destiny:
            client_obj = Client.objects.get(id=int(client_id))
            district_obj = District.objects.get(id=int(district_destiny))
            ClientAddress.objects.create(client=client_obj, address=new_address.upper(), district=district_obj)

            return JsonResponse({
                'success': True,
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Faltan datos al guardar cierre y vuelva a intentar'
            }, status=HTTPStatus.OK)


def modal_guide_carrier(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        truck_set = Truck.objects.all()
        owner_set = Owner.objects.all()
        t = loader.get_template('comercial/modal_guide_carrier.html')
        c = ({
            'truck_set': truck_set,
            'subsidiary_obj': subsidiary_obj,
            'owner_set': owner_set,
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


def get_quantity_product(request):
    if request.method == 'GET':
        id_product = request.GET.get('pk', '')
        # print(id_product)
        product_obj = Product.objects.get(pk=int(id_product))
        # print(product_obj)
        user = request.user.id
        user_obj = User.objects.get(id=user)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        # print(subsidiary_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()
        # print(subsidiary_store_obj)
        product_store_obj = ProductStore.objects.get(product__id=id_product, subsidiary_store=subsidiary_store_obj)
        # print(product_store_obj)
        units_obj = Unit.objects.filter(productdetail__product=product_obj)
        # print(units_obj)
        serialized_units = serializers.serialize('json', units_obj)
        return JsonResponse({
            'quantity': product_store_obj.stock,
            'units': serialized_units,
            'id_product_store': product_store_obj.id
        }, status=HTTPStatus.OK)


def guide_detail_list(request):
    # programmings = Programming.objects.filter(status__in=['P'], guide__isnull=False).order_by('id')
    date_now = datetime.now().strftime("%Y-%m-%d")
    return render(request, 'comercial/guide_detail_programming.html', {
        'date': date_now,
        'programmings': None
    })


def report_guide_by_plate(request):
    if request.method == 'GET':
        date = datetime.now()
        date_now = date.strftime("%Y-%m-%d")
        truck_set = Truck.objects.all()

        return render(request, 'comercial/report_guides_by_plate.html', {
            'date_now': date_now,
            'trucks': truck_set,
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_dict_programming_guides_queries(programmings_set):
    dictionary = []

    guide_items = []
    count = 0
    for p in programmings_set:
        count = programmings_set.count()
        new = {
            'id': p.id,
            'truck': p.truck.license_plate,
            'pilot': p.get_pilot().full_name,
            'departure_date': p.departure_date,
            'arrival_date': p.arrival_date,
            'origin': p.route_set.first().subsidiary.name,
            'destiny': p.route_set.last().subsidiary.name,
            'guide_items': [],
            'rowspan': 0
        }
        if p.guide_set.all:
            counter = 0
            for g in p.guide_set.all():
                counter = g.guidedetail_set.count()
                guide_items = {
                    'id': g.id,
                    'serial': g.serial,
                    'code': g.code,
                    # 'minimal_cost': g.minimal_cost,
                    'status': g.status,
                    'counter': counter,
                    'detail_guide': []
                }
                for gd in g.guidedetail_set.all():
                    guide_detail_item = {
                        'id': gd.id,
                        'product': gd.product,
                        'quantity': gd.quantity,
                        'unit': gd.unit_measure,
                        'type': gd.get_type_display(),
                        'weight': gd.weight,
                        'rowspan': g.guidedetail_set.count(),
                    }
                    guide_items.get('detail_guide').append(guide_detail_item)
            new['rowspan'] = counter
            new.get('guide_items').append(guide_items)
        dictionary.append(new)
    tpl = loader.get_template('comercial/report_guide_by_plate_grid.html')
    context = ({
        'dictionary': dictionary,
        'count': count,
    })

    return tpl.render(context)

def get_stock_by_store(request):
    if request.method == 'GET':
        id_product = request.GET.get('ip', '')
        id_subsidiary_store = request.GET.get('iss', '')
        print(id_product)
        print(id_subsidiary_store)
        product_obj = Product.objects.get(pk=int(id_product))
        print(product_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(id_subsidiary_store))
        print(subsidiary_store_obj)

        quantity = ''
        id_product_store = 0
        product_store_obj = None
        try:
            product_store_obj = ProductStore.objects.get(product=product_obj, subsidiary_store=subsidiary_store_obj)
        except ProductStore.DoesNotExist:
            quantity = 'SP'
        if product_store_obj is not None:
            print(product_store_obj)
            quantity = str(product_store_obj.stock)
            id_product_store = product_store_obj.id

        return JsonResponse({
            'quantity': quantity,
            'id_product_store': id_product_store
        }, status=HTTPStatus.OK)


def output_guide(request):
    # programmings = Programming.objects.filter(status__in=['P'], guide__isnull=False).order_by('id')
    motives = GuideMotive.objects.filter(type='S')
    user_id = request.user.id
    user_obj = User.objects.get(pk=int(user_id))
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    my_date = datetime.now()
    formatdate = my_date.strftime("%Y-%m-%d")
    product_set = Product.objects.filter(productstore__subsidiary_store__subsidiary=subsidiary_obj)

    return render(request, 'comercial/output_guide.html', {
        'motives': motives,
        'subsidiaries': Subsidiary.objects.exclude(name=subsidiary_obj.name),
        'current_date': formatdate,
        'subsidiary_origin': subsidiary_obj,
        'product_set': product_set,
        'choices_document_type_attached': Guide._meta.get_field('document_type_attached').choices,
    })


def input_guide(request):
    # programmings = Programming.objects.filter(status__in=['P'], guide__isnull=False).order_by('id')
    motives = GuideMotive.objects.filter(type='E')
    my_date = datetime.now()
    formatdate = my_date.strftime("%Y-%m-%d")
    user_id = request.user.id
    user_obj = User.objects.get(pk=int(user_id))
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    product_set = Product.objects.all()

    return render(request, 'comercial/input_guide.html', {
        'motives': motives,
        'current_date': formatdate,
        'product_set': product_set,
        'subsidiary_origin': subsidiary_obj,
        'choices_document_type_attached': Guide._meta.get_field('document_type_attached').choices,
    })


def get_products_by_subsidiary_store(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        is_table = bool(int(request.GET.get('is_table')))
        subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(pk))
        product_set = Product.objects.filter(productstore__subsidiary_store=subsidiary_store_obj)
        tpl = loader.get_template('comercial/io_guide_list.html')
        context = ({
            'product_set': product_set,
            'is_table': is_table,
            'subsidiary_store': subsidiary_store_obj,
        })

        product_stores = [(
            ps.pk,
            ps.product.id,
            ps.product.name,
            ps.stock,
            ps.product.calculate_minimum_unit(),
            ps.product.productdetail_set.filter(quantity_minimum=ps.product.calculate_minimum_unit()).first().unit.id,
        ) for ps in ProductStore.objects.filter(subsidiary_store=subsidiary_store_obj).order_by('product__name')]

        return JsonResponse({
            'success': True,
            'subsidiary_store': subsidiary_store_obj.name,
            'grid': tpl.render(context),
            # 'product_store_set_serialized': serializers.serialize('json', product_stores),
            'product_store_set_serialized': product_stores,
        }, status=HTTPStatus.OK)


def output_workflow(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    date_now = datetime.now().strftime("%Y-%m-%d")
    a = [1, 3, 4, 6, 7]
    guides_set = Guide.objects.filter(subsidiary=subsidiary_obj,
                                      guide_motive__type='S',
                                      guide_motive__id__in=a)
    if request.method == 'GET':
        guides_set = guides_set.filter(created_at__date=date_now)
    elif request.method == 'POST':
        date_initial = request.POST.get('date_initial', '')
        date_final = request.POST.get('date_final', '')
        guides_set = guides_set.filter(created_at__date__range=(date_initial, date_final))
    return render(request, 'comercial/output_workflow.html', {
        'guides': guides_set,
        'status': Guide._meta.get_field('status').choices,
        'date_now': date_now,
    })


def input_workflow(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    date_now = datetime.now().strftime("%Y-%m-%d")
    guides_set = Guide.objects.filter(subsidiary=subsidiary_obj, guide_motive__type='E')
    if request.method == 'GET':
        guides_set = guides_set.filter(created_at__date=date_now)
    elif request.method == 'POST':
        date_initial = request.POST.get('date_initial', '')
        date_final = request.POST.get('date_final', '')
        guides_set = guides_set.filter(created_at__date__range=(date_initial, date_final))
    return render(request, 'comercial/input_workflow.html', {
        'guides': guides_set,
        'status': Guide._meta.get_field('status').choices,
        'date_now': date_now,
    })


def input_workflow_from_output(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    date_now = datetime.now().strftime("%Y-%m-%d")
    # Outputs: 1, 3, 6, 7
    # Transfers: 4
    a = [4]
    guides_set = Guide.objects.filter(route__type='D',
                                      route__subsidiary_store__subsidiary=subsidiary_obj,
                                      guide_motive__type='S', guide_motive__id__in=a)
    if request.method == 'GET':
        guides_set = guides_set.filter(created_at__date=date_now)
    elif request.method == 'POST':
        date_initial = request.POST.get('date_initial', '')
        date_final = request.POST.get('date_final', '')
        guides_set = guides_set.filter(created_at__date__range=(date_initial, date_final))
    return render(request, 'comercial/input_workflow_from_output.html', {
        'guides': guides_set,
        'status': Guide._meta.get_field('status').choices,
        'date_now': date_now,
    })


def get_merchandise_of_output(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')

        guide_obj = Guide.objects.get(id=int(pk))

        if guide_obj.status != '1':
            data = {'error': "Solo puede recepcionar mercaderia en transito!"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        t = loader.get_template('comercial/receive_merchandise.html')
        c = ({
            'guide': guide_obj,
        })

        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


# --------------- Transferencias entre almacenes ---------------

def _next_transfer_code():
    from django.db.models import Max
    today = date.today().strftime('%Y%m%d')
    prefix = f'TRF-{today}-'
    last = Transfer.objects.filter(code__startswith=prefix).aggregate(Max('code'))['code__max']
    if last:
        try:
            n = int(last.split('-')[-1]) + 1
        except (ValueError, IndexError):
            n = 1
    else:
        n = 1
    return f'{prefix}{n:04d}'


def _next_transfer_serial_correlative():
    """Devuelve (serial, correlativo) para el siguiente documento de transferencia."""
    from django.db.models import Max
    serial = 'TRA'
    last = Transfer.objects.filter(serial=serial).aggregate(Max('correlative'))['correlative__max']
    if last:
        try:
            n = int(last) + 1
        except (ValueError, TypeError):
            n = 1
    else:
        n = 1
    correlative = str(n).zfill(5)
    return serial, correlative


def transfer_list(request):
    user_obj = request.user
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    transfers = Transfer.objects.filter(
        Q(origin_store__subsidiary=subsidiary_obj) | Q(destination_store__subsidiary=subsidiary_obj)
    ).select_related('origin_store', 'destination_store', 'guide_motive', 'user').prefetch_related('details').order_by('-created_at')
    return render(request, 'comercial/transfer_list.html', {
        'transfers': transfers,
        'status_choices': Transfer.STATUS,
        'subsidiary': subsidiary_obj,
    })


def transfer_create(request):
    user_obj = request.user
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    motives = GuideMotive.objects.filter(type='S', code__isnull=True)
    store_origin = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj).order_by('name')
    stores = SubsidiaryStore.objects.all().order_by('name')
    # Almacén por defecto (origen): primer almacén de la sede del usuario
    default_origin_store = store_origin.first()
    default_origin_store_id = default_origin_store.id if default_origin_store else None
    # Destino: todos los almacenes de la empresa (misma sede) excepto el del usuario
    stores_destination = stores.exclude(id=default_origin_store_id) if default_origin_store_id else stores
    next_serial, next_correlative = _next_transfer_serial_correlative()
    next_document_number = f'{next_serial}-{next_correlative}'
    return render(request, 'comercial/transfer_create.html', {
        'motives': motives,
        'stores': stores,
        'stores_destination': stores_destination,
        'default_origin_store_id': default_origin_store_id,
        'subsidiary': subsidiary_obj,
        'next_serial': next_serial,
        'next_correlative': next_correlative,
        'next_document_number': next_document_number,
    })


def get_products_batches_by_store(request):
    """Devuelve productos con stock y lotes disponibles en un almacén (para transferencia salida/destino)."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=HTTPStatus.BAD_REQUEST)
    store_id = request.GET.get('store_id')
    include_zero_stock = request.GET.get('include_zero_stock', '') == '1'
    if not store_id:
        return JsonResponse({'error': 'Falta store_id'}, status=HTTPStatus.BAD_REQUEST)
    try:
        store = SubsidiaryStore.objects.get(id=int(store_id))
    except (SubsidiaryStore.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Almacén no encontrado'}, status=HTTPStatus.NOT_FOUND)
    from apps.sales.models import Kardex
    qs = ProductStore.objects.filter(subsidiary_store=store).order_by('product__name')
    if not include_zero_stock:
        qs = qs.filter(stock__gt=0)
    product_stores = qs
    result = []
    for ps in product_stores:
        # Unidades con factor de conversión (quantity_minimum = equiv. en unidad base)
        units_qs = ProductDetail.objects.filter(product=ps.product, is_enabled=True).select_related('unit').order_by('quantity_minimum')
        units = [
            {'id': pd.unit.id, 'name': pd.unit.name, 'quantity_minimum': str(pd.quantity_minimum)}
            for pd in units_qs
        ]
        batches = list(Batch.objects.filter(product_store=ps).filter(remaining_quantity__gt=0).order_by('expiration_date').values('id', 'batch_number', 'expiration_date', 'remaining_quantity'))
        last_k = Kardex.objects.filter(product_store=ps).order_by('-id').first()
        price_unit = str(last_k.remaining_price) if last_k else '0'
        result.append({
            'product_id': ps.product.id,
            'product_name': ps.product.name,
            'product_code': getattr(ps.product, 'code', ''),
            'product_store_id': ps.id,
            'stock': str(ps.stock),
            'units': units,
            'batches': batches,
            'price_unit': price_unit,
        })
    return JsonResponse({'products': result}, status=HTTPStatus.OK)


def get_product_store_price(request):
    """Precio unitario (costo) del producto en el almacén."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=HTTPStatus.BAD_REQUEST)
    product_store_id = request.GET.get('product_store_id')
    if not product_store_id:
        return JsonResponse({'price': '0'}, status=HTTPStatus.OK)
    try:
        from apps.sales.models import Kardex
        last = Kardex.objects.filter(product_store_id=int(product_store_id)).order_by('-id').first()
        price = str(last.remaining_price) if last else '0'
    except Exception:
        price = '0'
    return JsonResponse({'price': price}, status=HTTPStatus.OK)


def transfer_save(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=HTTPStatus.BAD_REQUEST)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=HTTPStatus.BAD_REQUEST)
    origin_id = data.get('origin_store_id')
    destination_id = data.get('destination_store_id')
    motive_id = data.get('guide_motive_id')
    observation = (data.get('observation') or '').strip()
    details = data.get('details', [])
    if not origin_id or not destination_id or int(origin_id) == int(destination_id):
        return JsonResponse({'success': False, 'error': 'Seleccione almacén origen y destino distintos'}, status=HTTPStatus.BAD_REQUEST)
    if not motive_id:
        return JsonResponse({'success': False, 'error': 'Seleccione motivo de transferencia'}, status=HTTPStatus.BAD_REQUEST)
    if not details:
        return JsonResponse({'success': False, 'error': 'Agregue al menos un producto'}, status=HTTPStatus.BAD_REQUEST)
    try:
        origin_store = SubsidiaryStore.objects.get(id=int(origin_id))
        destination_store = SubsidiaryStore.objects.get(id=int(destination_id))
        guide_motive = GuideMotive.objects.get(id=int(motive_id))
    except (SubsidiaryStore.DoesNotExist, GuideMotive.DoesNotExist, ValueError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=HTTPStatus.BAD_REQUEST)
    code = _next_transfer_code()
    serial, correlative = _next_transfer_serial_correlative()
    transfer = Transfer.objects.create(
        code=code,
        serial=serial,
        correlative=correlative,
        origin_store=origin_store,
        destination_store=destination_store,
        guide_motive=guide_motive,
        status='C',
        observation=observation or None,
        user=request.user,
    )
    now = datetime.now()
    for d in details:
        product_id = d.get('product_id')
        product_store_id = d.get('product_store_id')
        quantity = decimal.Decimal(str(d.get('quantity', 0)))
        unit_id = d.get('unit_id')
        batch_id = d.get('batch_id')
        unit_price = decimal.Decimal(str(d.get('unit_price', 0)))
        if quantity <= 0 or not product_id or not product_store_id:
            continue
        try:
            product = Product.objects.get(id=int(product_id))
            product_store_origin = ProductStore.objects.get(id=int(product_store_id))
        except (Product.DoesNotExist, ProductStore.DoesNotExist, ValueError):
            continue
        unit_obj = None
        if unit_id:
            try:
                unit_obj = Unit.objects.get(id=int(unit_id))
            except Unit.DoesNotExist:
                pass
        batch_obj = None
        if batch_id:
            try:
                batch_obj = Batch.objects.get(id=int(batch_id), product_store=product_store_origin)
            except Batch.DoesNotExist:
                pass
        if product_store_origin.stock < quantity:
            transfer.delete()
            return JsonResponse({'success': False, 'error': f'Stock insuficiente para {product.name}'}, status=HTTPStatus.BAD_REQUEST)
        total_line = quantity * unit_price
        detail = TransferDetail.objects.create(
            transfer=transfer,
            product=product,
            unit=unit_obj,
            quantity=quantity,
            batch=batch_obj,
            unit_price=unit_price,
            total=total_line,
        )
        kardex_ouput(
            product_store_id=product_store_origin.id,
            quantity=quantity,
            type_document='00',
            type_operation='11',
            batch_obj=batch_obj,
            transfer_detail_obj=detail,
        )
    transfer.status = 'E'
    transfer.sent_at = now
    transfer.save(update_fields=['status', 'sent_at'])
    return JsonResponse({'success': True, 'code': transfer.code, 'id': transfer.id}, status=HTTPStatus.OK)


def transfer_receive_list(request):
    user_obj = request.user
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    transfers = Transfer.objects.filter(
        destination_store__subsidiary=subsidiary_obj,
        status='E',
    ).select_related('origin_store', 'destination_store', 'guide_motive', 'user').prefetch_related('details', 'details__product', 'details__batch', 'details__unit').annotate(total_transfer=Coalesce(Sum('details__total'), 0)).order_by('-sent_at')
    return render(request, 'comercial/transfer_receive_list.html', {
        'transfers': transfers,
    })


def transfer_accept(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=HTTPStatus.METHOD_NOT_ALLOWED)
    try:
        transfer = Transfer.objects.get(pk=pk, status='E')
    except Transfer.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Transferencia no encontrada o ya recibida'}, status=HTTPStatus.NOT_FOUND)
    subsidiary_obj = get_subsidiary_by_user(request.user)
    if transfer.destination_store.subsidiary_id != subsidiary_obj.id:
        return JsonResponse({'success': False, 'error': 'No puede recepcionar en esta sede'}, status=HTTPStatus.FORBIDDEN)
    dest_store = transfer.destination_store
    for detail in transfer.details.all():
        try:
            product_store_dest, _ = ProductStore.objects.get_or_create(
                product=detail.product,
                subsidiary_store=dest_store,
                defaults={'stock': 0},
            )
        except Exception:
            return JsonResponse({'success': False, 'error': f'Error al obtener almacén destino para {detail.product.name}'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        total_cost = detail.total
        batch_number = None
        batch_expiration = None
        if detail.batch_id:
            batch_number = detail.batch.batch_number
            batch_expiration = detail.batch.expiration_date
        has_kardex = False
        try:
            from apps.sales.models import Kardex
            has_kardex = Kardex.objects.filter(product_store=product_store_dest).exists()
        except Exception:
            pass
        if not has_kardex:
            kardex_initial(product_store_dest, detail.quantity, detail.unit_price)
            product_store_dest.stock = product_store_dest.stock + detail.quantity
            product_store_dest.save(update_fields=['stock'])
            if batch_number is not None and batch_expiration is not None:
                from apps.sales.models import Kardex, Batch as BatchModel
                last_k = Kardex.objects.filter(product_store=product_store_dest).order_by('-id').first()
                if last_k:
                    BatchModel.objects.create(
                        batch_number=str(batch_number),
                        expiration_date=batch_expiration,
                        quantity=detail.quantity,
                        remaining_quantity=detail.quantity,
                        kardex=last_k,
                        product_store=product_store_dest,
                    )
        else:
            kardex_input(
                product_store_id=product_store_dest.id,
                quantity=detail.quantity,
                total_cost=total_cost,
                type_document='00',
                type_operation='11',
                transfer_detail_obj=detail,
                batch_number=batch_number,
                batch_expiration_date=batch_expiration,
            )
    transfer.status = 'R'
    transfer.received_at = datetime.now()
    transfer.received_by = request.user
    transfer.save(update_fields=['status', 'received_at', 'received_by'])
    return JsonResponse({'success': True, 'message': 'Transferencia recepcionada correctamente'}, status=HTTPStatus.OK)


def direct_input_warehouse(request):
    user_obj = request.user
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    stores = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj).order_by('name')
    products = Product.objects.filter(productstore__subsidiary_store__subsidiary=subsidiary_obj).distinct().order_by('name')
    if request.method == 'POST':
        store_id = request.POST.get('store_id')
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity')
        unit_id = request.POST.get('unit_id')
        batch_number = request.POST.get('batch_number', '').strip()
        batch_expiration = request.POST.get('batch_expiration', '').strip()
        unit_price = request.POST.get('unit_price', '0')
        if not store_id or not product_id or not quantity:
            return render(request, 'comercial/direct_input_warehouse.html', {
                'stores': stores,
                'products': products,
                'error': 'Complete almacén, producto y cantidad.',
            })
        try:
            qty = decimal.Decimal(quantity)
            price = decimal.Decimal(unit_price or '0')
        except Exception:
            return render(request, 'comercial/direct_input_warehouse.html', {
                'stores': stores,
                'products': products,
                'error': 'Cantidad y precio deben ser numéricos.',
            })
        if qty <= 0:
            return render(request, 'comercial/direct_input_warehouse.html', {
                'stores': stores,
                'products': products,
                'error': 'La cantidad debe ser mayor a cero.',
            })
        try:
            store = SubsidiaryStore.objects.get(id=int(store_id), subsidiary=subsidiary_obj)
            product = Product.objects.get(id=int(product_id))
        except (SubsidiaryStore.DoesNotExist, Product.DoesNotExist):
            return render(request, 'comercial/direct_input_warehouse.html', {
                'stores': stores,
                'products': products,
                'error': 'Almacén o producto no válido.',
            })
        product_store, _ = ProductStore.objects.get_or_create(
            product=product,
            subsidiary_store=store,
            defaults={'stock': 0},
        )
        from apps.sales.models import Kardex
        has_kardex = Kardex.objects.filter(product_store=product_store).exists()
        total_cost = qty * price
        batch_expiration_date = date.fromisoformat(batch_expiration) if batch_expiration else None
        if not has_kardex:
            kardex_initial(product_store, qty, price)
            if batch_number and batch_expiration_date:
                from apps.sales.models import Batch as BatchModel
                last_k = Kardex.objects.filter(product_store=product_store).order_by('-id').first()
                if last_k:
                    BatchModel.objects.create(
                        batch_number=batch_number,
                        expiration_date=batch_expiration_date,
                        quantity=qty,
                        remaining_quantity=qty,
                        kardex=last_k,
                        product_store=product_store,
                    )
        else:
            kardex_input(
                product_store_id=product_store.id,
                quantity=qty,
                total_cost=total_cost,
                type_document='00',
                type_operation='99',
                batch_number=batch_number or None,
                batch_expiration_date=batch_expiration_date,
            )
        return render(request, 'comercial/direct_input_warehouse.html', {
            'stores': stores,
            'products': products,
            'success': 'Ingreso registrado correctamente.',
        })
    return render(request, 'comercial/direct_input_warehouse.html', {
        'stores': stores,
        'products': products,
    })


def distribution_movil_list(request):
    truck_obj = Truck.objects.all()
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()
    products = Product.objects.filter(productstore__subsidiary_store=subsidiary_store_obj)

    return render(request, 'comercial/distribution_movil.html', {
        'truck_obj': truck_obj,
        'product_obj': products,

    })

def get_units_by_products_distribution_mobil(request):
    if request.method == 'GET':
        product_id = request.GET.get('ip', '')
        unit_obj = Unit.objects.filter(productdetail__product_id=int(product_id))
        units_serialized_obj = serializers.serialize('json', unit_obj)

        return JsonResponse({
            'units': units_serialized_obj,
        }, status=HTTPStatus.OK)


def get_units_and_sotck_by_product(request):
    if request.method == 'GET':
        id_product = request.GET.get('ip', '')
        category = request.GET.get('_category', '')
        product_obj = Product.objects.get(pk=int(id_product))
        units = Unit.objects.filter(productdetail__product=product_obj)
        units_serialized_obj = serializers.serialize('json', units)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_store_obj = ProductStore.objects.filter(product_id=id_product,
                                                        subsidiary_store__subsidiary=subsidiary_obj,
                                                        subsidiary_store__category=category).first()
        return JsonResponse({
            'units': units_serialized_obj,
            'stock': product_store_obj.stock,

        }, status=HTTPStatus.OK)


def output_distribution(request):
    if request.method == 'GET':
        trucks_set = Truck.objects.all()
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()
        products_set = Product.objects.filter(productstore__subsidiary_store=subsidiary_store_obj).exclude(
            id__in=[5, 4])
        t = loader.get_template('comercial/distribution_output.html')
        c = ({
            'truck_set': trucks_set,
            'product_set': products_set,
            'employees': Employee.objects.all(),
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


def get_distribution_mobil_sales(request):
    if request.method == 'GET':
        pk = int(request.GET.get('pk', ''))

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        clients = Client.objects.all()
        product_set = Product.objects.filter(productstore__subsidiary_store__subsidiary=subsidiary_obj,
                                             productstore__subsidiary_store__category='V')
        t = loader.get_template('comercial/distribution_sales.html')
        c = ({
            'client_set': clients,
            'product_set': product_set,
            'choices_payments': TransactionPayment._meta.get_field('type').choices

        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def get_products_by_supplier(request):
    if request.method == 'GET':
        supplier_id = request.GET.get('ip', '')
        supplier_obj = Supplier.objects.get(pk=int(supplier_id))
        product_set = Product.objects.filter(productsupplier__supplier=supplier_obj)
        products_supplier_obj = ProductSupplier.objects.filter(
            product=product_set.first(), supplier=supplier_obj)

        product_serialized_obj = serializers.serialize('json', product_set)

        return JsonResponse({
            'price': products_supplier_obj[0].price_purchase,
            'products': product_serialized_obj,

        }, status=HTTPStatus.OK)


def largest_among(num1, num2, num3):
    largest = 0
    if (num1 >= num2) and (num1 >= num3):
        largest = num1
    elif (num2 >= num1) and (num2 >= num3):
        largest = num2
    else:
        largest = num3
    return largest

def get_order_detail_by_client(request):
    if request.method == 'GET':
        client_id = request.GET.get('client_id', '')
        # distribution_mobil_id = int(request.GET.get('pk', ''))
        # distribution_mobil_obj = DistributionMobil.objects.get(id=distribution_mobil_id)
        client_obj = Client.objects.get(pk=int(client_id))
        order_set = Order.objects.filter(client=client_obj).filter(Q(type='R') | Q(type='V')).order_by('id')

        return JsonResponse({
            'grid': get_dict_orders_details(order_set, client_obj),
        }, status=HTTPStatus.OK)


def get_dict_orders_details(order_set, client_obj):
    tpl = loader.get_template('comercial/table_orderdetail_client.html')
    context = ({
        'order_set': order_set,
        'client_obj': client_obj,
    })

    return tpl.render(context)


def get_output_distributions(request):
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
            tpl = loader.get_template('buys/buy_order_store_grid_list.html')
            context = ({
                'purchases_store': purchases_store,
            })
            return JsonResponse({
                'success': True,
                'form': tpl.render(context, request),
            })
        else:
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            return render(request, 'comercial/report_quantity_output_distribution.html', {
                'date_now': date_now,
            })


def modal_new_carrier(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        t = loader.get_template('comercial/modal_new_carrier.html')
        c = ({
            'date': formatdate,
            'subsidiary_obj': subsidiary_obj,
            'owner_set': Owner.objects.all()
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Problemas con el formulario'
        }, status=HTTPStatus.OK)


def get_carrier_api(request):
    if request.method == 'GET':
        nro_document = request.GET.get('nro_document', '')
        type_document = str(request.GET.get('type', ''))
        owner_obj_search = Owner.objects.filter(ruc=nro_document)
        if owner_obj_search.exists():
            names = owner_obj_search.last().name
            data = {
                'error': 'EL PROVEEDOR ' + str(names) + ' YA SE ENCUENTRA REGISTRADO'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        else:
            if type_document == '06':
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


def create_carrier(request):
    if request.method == 'POST':
        document_number = str(request.POST.get('document_number', ''))
        name_transport = str(request.POST.get('name-transport', ''))
        address_transport = str(request.POST.get('address-transport', ''))

        if document_number and name_transport:

            owner_obj = Owner(
                name=name_transport,
                ruc=document_number,
                address=address_transport
            )
            owner_obj.save()

            return JsonResponse({
                'success': True,
                'message': 'Transportista Registrado correctamente',
            }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Ingrese un transportista'
            }, status=HTTPStatus.OK)


def get_truck(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')

        truck_set = Truck.objects.filter(id=pk)
        truck_serialized_data = serializers.serialize('json', truck_set)
        return JsonResponse({
            'success': True,
            'truck_serialized': truck_serialized_data,
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def modal_new_driver(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        t = loader.get_template('comercial/modal_new_driver.html')
        c = ({
            'date': formatdate,
            'subsidiary_obj': subsidiary_obj,
            'license_type': Driver._meta.get_field('license_type').choices,
            'driver_set': Driver.objects.all()
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Problemas con el formulario'
        }, status=HTTPStatus.OK)


def create_driver(request):
    if request.method == 'POST':
        document_driver = str(request.POST.get('document-driver', ''))
        name_driver = str(request.POST.get('name-driver', ''))
        license_number = str(request.POST.get('license-number', ''))
        license_type = str(request.POST.get('license-type', ''))
        expiration_date = str(request.POST.get('expiration-date', ''))

        if document_driver and name_driver:

            driver_obj = Driver(
                names=name_driver.upper(),
                document_driver=document_driver,
                n_license=license_number,
                license_type=license_type,
                license_expiration_date=expiration_date
            )
            driver_obj.save()

            return JsonResponse({
                'success': True,
                'message': 'Transportista Registrado correctamente',
            }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Ingrese un Conductor'
            }, status=HTTPStatus.OK)


def new_pilot_associate(request):
    data = dict()
    if request.method == 'GET':
        id = request.GET.get('truck_id')
        associates = request.GET.get('associates', '')
        _arr = []
        if associates != '[]':
            str1 = associates.replace(']', '').replace('[', '')
            _arr = str1.replace('"', '').split(",")
            truck_obj = Truck.objects.get(id=int(id))
            associated_set = TruckAssociate.objects.filter(truck=truck_obj)
            associated_set.delete()
            for a in _arr:
                driver_obj = Driver.objects.get(id=int(a))
                truck_associate_obj = TruckAssociate(truck=truck_obj, driver=driver_obj)
                truck_associate_obj.save()
        else:
            data['error'] = "Ingrese valores validos."
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        return JsonResponse({'success': True, 'message': 'El conductor se asocio correctamente.'})
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_vehicle_by_carrier(request):
    if request.method == 'GET':
        pk = request.GET.get('id', '')
        owner_obj = Owner.objects.get(id=pk)
        truck_set = Truck.objects.filter(owner_id=pk)
        truck_serialized_data = serializers.serialize('json', truck_set)
        return JsonResponse({
            'success': True,
            'truck': truck_serialized_data,
            'carrier_name': owner_obj.name,
            'carrier_document': owner_obj.ruc,
            'carrier_id': owner_obj.id,
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_plate_by_vehicle(request):
    if request.method == 'GET':
        pk = request.GET.get('id', '')
        vehicle_obj = Truck.objects.get(id=pk)
        truck_associate_set = TruckAssociate.objects.filter(truck_id=pk)
        truck_associate_dict = []
        for t in truck_associate_set:
            item = {
                'id': t.id,
                'plate_id': t.truck.id,
                'plate_name': t.truck.license_plate,
                'driver_id': t.driver.id,
                'driver_document': t.driver.document_driver,
                'driver_license': t.driver.n_license,
                'driver_name': t.driver.names.upper()
            }
            truck_associate_dict.append(item)

        return JsonResponse({
            'success': True,
            'truck_associate_dict': truck_associate_dict,
            'license_plate': vehicle_obj.license_plate.upper(),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def save_guide(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        guide_request = request.GET.get('guide', '')
        data_guide = json.loads(guide_request)

        contract_detail = data_guide["contract_detail"]

        issue_date = data_guide["issue_date"]
        transfer_date = data_guide["transfer_date"]
        client = data_guide["client"]
        motive = data_guide["motive"]

        origin = data_guide["origin"]
        origin_address = data_guide["origin_address"]

        destiny = data_guide["destiny"]
        destiny_address = data_guide["destiny_address"]

        modality_transport = data_guide["transport_modality"]

        carrier = data_guide["carrier"]
        vehicle = data_guide["vehicle"]
        driver = data_guide["driver"]

        weight = data_guide["weight"]
        n_package = data_guide["n_package"]
        observations = data_guide["observations"]

        store = data_guide["store"]

        serial = data_guide["serial"]
        correlative = str(data_guide["correlative"])

        oc = data_guide["oc"]
        register_mtc = data_guide["register_mtc"]
        cod_siaf = data_guide["cod_siaf"]

        contract_detail_obj = None
        if contract_detail:
            contract_detail_obj = ContractDetail.objects.get(id=int(contract_detail))

        client_obj = None
        motive_obj = None
        carrier_obj = None
        vehicle_obj = None
        driver_obj = None
        if client:
            client_obj = Client.objects.get(id=int(client))

        if motive:
            motive_obj = GuideMotive.objects.get(id=int(motive))

        if carrier:
            carrier_obj = Owner.objects.get(id=int(carrier))
        else:
            carrier_obj = Owner.objects.create(name=data_guide["name_transport"], ruc=data_guide["document_transport"])

        if vehicle and driver:
            vehicle_obj = Truck.objects.get(id=int(vehicle))
            driver_obj = Driver.objects.get(id=int(driver))
        else:
            vehicle_obj = Truck.objects.create(license_plate=data_guide["plate"], owner=carrier_obj)
            driver_obj = Driver.objects.create(names=data_guide["names_driver"],
                                               document_driver=data_guide["document_driver"],
                                               n_license=data_guide["license_driver"])

        store_obj = SubsidiaryStore.objects.get(id=int(store))

        guide_obj = Guide(
            serial=serial,
            correlative=correlative,
            date_issue=issue_date,
            transfer_date=transfer_date,
            client=client_obj,
            guide_motive=motive_obj,
            origin=origin,
            origin_address=origin_address,
            destiny=destiny,
            destiny_address=destiny_address,
            modality_transport=modality_transport,
            carrier=carrier_obj,
            vehicle=vehicle_obj,
            driver=driver_obj,
            weight=weight,
            package=n_package,
            observation=observations,
            user=user_obj,
            subsidiary=subsidiary_obj,
            contract_detail=contract_detail_obj,
            order_buy=oc,
            register_mtc=register_mtc,
            subsidiary_store=store_obj,
            cod_siaf=cod_siaf
        )
        guide_obj.save()

        for detail in data_guide['Details']:
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)
            quantity = decimal.Decimal(detail['Quantity'])
            quantity_unit = decimal.Decimal(detail['QuantityUnit'])
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)
            
            # Crear el detalle de la guía
            guide_detail_obj = GuideDetail.objects.create(
                guide=guide_obj, 
                product=product_obj,
                quantity=quantity_unit, 
                unit=unit_obj
            )
            
            # Manejar múltiples lotes si están separados por comas
            batch_ids = detail['Batch'].split(',') if ',' in detail['Batch'] else [detail['Batch']]
            
            for batch_id in batch_ids:
                if batch_id.strip():  # Verificar que no esté vacío
                    try:
                        batch_obj = Batch.objects.get(id=int(batch_id.strip()))
                        # Crear registro de lote detalle
                        GuideDetailBatch.objects.create(
                            guide_detail=guide_detail_obj,
                            batch=batch_obj,
                            quantity=quantity_unit  # Por ahora usar la cantidad total, se puede ajustar después
                        )
                    except (Batch.DoesNotExist, ValueError):
                        # Si el lote no existe, continuar con el siguiente
                        continue
            
            # product_store_id = ProductStore.objects.filter(product=product_obj, subsidiary_store=store_obj).last().id
            # kardex_ouput(product_store_id, quantity, guide_detail_obj=new_detail_guide_obj,)

        return JsonResponse({
            'pk': guide_obj.id,
            'message': 'Guia Registrada',
            'contract': guide_obj.contract_detail.id,
        }, status=HTTPStatus.OK)


def get_correlative_guide_by_subsidiary(subsidiary_obj=None):
    search = Guide.objects.filter(subsidiary=subsidiary_obj)
    if search.exists():
        guide_obj = search.last()
        correlative = int(guide_obj.correlative)
        if correlative:
            new_correlative = correlative + 1
            result = new_correlative
        else:
            result = 1
    else:
        result = 1

    return result


def get_store(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_set = Subsidiary.objects.all()
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    subsidiary_stores = SubsidiaryStore.objects.all()
    return render(request, 'comercial/get_store.html', {
        'subsidiary_obj': subsidiary_obj,
        'subsidiary_stores': subsidiary_stores,
        'subsidiary_set': subsidiary_set,
        'categories': SubsidiaryStore._meta.get_field('category').choices,
    })


def new_store(request):
    if request.method == 'POST':
        name_store = str(request.POST.get('name-store'))
        category = request.POST.get('category')
        subsidiary = request.POST.get('subsidiary')
        subsidiary_obj = Subsidiary.objects.get(id=int(subsidiary))
        SubsidiaryStore.objects.create(subsidiary=subsidiary_obj, name=name_store.upper(), category=category)
        return JsonResponse({
            'message': 'Almacen registrado correctamente.',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def save_new_address_origin(request):
    if request.method == 'GET':
        address = request.GET.get('address')
        district = request.GET.get('district')
        district_obj = District.objects.get(id=int(district))
        Subsidiary.objects.create(name='DIRECCION', address=address, district=district_obj, is_address=True)
        return JsonResponse({
            'success': True,
            'ubigeo': district_obj.ubigeo
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_guide_by_contract(request):
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
                    'o_c': c.contractdetailpurchase_set.last().purchase.bill_number if c.contractdetailpurchase_set.exists() and c.contractdetailpurchase_set.last().purchase else '-'
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
                        # 'district': cd.district.description,
                    } for cd in client_address_set]
                else:
                    address_dict = []

                client_data.append({
                    'id': c.id,
                    'names': c.names,
                    'type_client_display': c.get_type_client_display(),
                    'type_client': c.type_client,
                    'number': c.clienttype_set.last().document_number,
                    'address': address_dict,
                    'cod_siaf': c.cod_siaf
                })

            item = {
                'product_id': product_id,
                'product_name': product_obj.name,
                'product_weight': product_obj.weight,
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

        return JsonResponse({'redirect_url': f'/comercial/get_guide?selected_data={json_data}'})


def modal_batch_guide(request):
    if request.method == 'GET':
        subsidiary_store_id = request.GET.get('store_id', '')
        product_id = request.GET.get('productID', '')
        required_quantity = request.GET.get('required_quantity', '0')
        product_store_set = ProductStore.objects.filter(subsidiary_store__id=subsidiary_store_id,
                                                        product__id=product_id)
        if product_store_set.exists():
            product_store_obj = product_store_set.last()
            last_batches = Batch.objects.filter(
                batch_number=OuterRef('batch_number'), product_store=product_store_obj).order_by('-id')

            latest_batches = Batch.objects.filter(
                product_store=product_store_obj
            ).annotate(last_id=Subquery(last_batches.values('id')[:1])).filter(id=F('last_id'),
                                                                               remaining_quantity__gt=0)

            if latest_batches.exists():
                product_obj = product_store_obj.product
                
                # Filtrar solo los lotes que tienen unidades (und) - asumiendo que 'und' es la unidad base
                # Buscar ProductDetail con unidad 'und' o similar
                unit_und = Unit.objects.filter(name__icontains='und').first()
                if not unit_und:
                    # Si no existe 'und', buscar la unidad con menor quantity_minimum (unidad base)
                    unit_und = ProductDetail.objects.filter(product=product_obj).order_by('quantity_minimum').first()
                    if unit_und:
                        unit_und = unit_und.unit
                
                # Filtrar lotes que tengan la unidad base
                if unit_und:
                    latest_batches = latest_batches.filter(
                        product_store__product__productdetail__unit=unit_und
                    ).distinct()
                
                tpl = loader.get_template('comercial/modal_guide_batch.html')
                context = ({
                    'batch_set': latest_batches,
                    'product_obj': product_obj,
                    'product_store_obj': product_store_obj,
                    'product_detail_set': ProductDetail.objects.filter(product=product_obj, unit=unit_und) if unit_und else ProductDetail.objects.filter(product=product_obj),
                    'required_quantity': required_quantity
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

        else:
            return JsonResponse({
                'success': False,
                'message': 'El Producto no cuenta con Lotes en el Almacen seleccionado. Revisar el Producto'
            }, status=HTTPStatus.OK)


def guide_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    guide_set = Guide.objects.filter(status__in=['1']).order_by('-id')

    guide_dict = []

    for g in guide_set:

        item_guide = {
            'id': g.id,
            'serial': g.serial,
            'correlative': g.correlative,
            'status': g.get_status_display(),
            'document_type_attached': g.get_document_type_attached_display(),
            'client': g.client.names,
            'origin': g.origin,
            'origin_address': g.origin_address,
            'destiny': g.destiny,
            'destiny_address': g.destiny_address,
            'modality_transport': g.modality_transport,
            'modality_transport_display': g.get_modality_transport_display(),
            'carrier': g.carrier.name if g.carrier else '-',
            'carrierID': g.carrier.id if g.carrier else '',
            'vehicle': g.vehicle.license_plate if g.vehicle else '-',
            'vehicleID': g.vehicle.id if g.vehicle else '',
            'driver': g.driver.names if g.driver else '-',
            'driverID': g.driver.id if g.driver else '',
            'weight': str(round(g.weight, 2)),
            'package': str(round(g.package)),
            'date_issue': g.date_issue,
            'transfer_date': g.transfer_date,
            'contract_detail': g.contract_detail,
            'guide_motive': g.guide_motive.description,
            'observation': g.observation,
            'count': g.guidedetail_set.count(),
            'store': g.subsidiary_store,
            'details': []
        }
        for gd in g.guidedetail_set.all():
            item_detail = {
                'id': gd.id,
                'product': gd.product.name,
                'quantity': str(round(gd.quantity)),
                'unit': gd.unit.name,
                'batch': gd.batch.batch_number if gd.batch else '-'
            }
            item_guide.get('details').append(item_detail)
        guide_dict.append(item_guide)

    return render(request, 'comercial/guide_list.html', {
        'guides': guide_dict,
    })


def get_last_picking_number():
    last_number = Picking.objects.exclude(picking_number='').annotate(
        picking_number_int=Cast('picking_number', IntegerField())
    ).aggregate(
        last_picking_number=Coalesce(Max('picking_number_int'), Value(0))
    )['last_picking_number']

    next_number = last_number + 1

    return next_number


def get_latest_batches_for_product(product):
    # Subconsulta para encontrar el último ID por batch_number
    latest_batch_subquery = Batch.objects.filter(
        product_store__product=product,
        batch_number=OuterRef('batch_number'),
        remaining_quantity__gt=0
    ).order_by('-id')  # O reemplaza '-id' por '-kardex_id' si aplica

    # Obtener IDs únicos del último batch por batch_number
    latest_batch_ids = Batch.objects.filter(
        product_store__product=product,
        remaining_quantity__gt=0
    ).values('batch_number').annotate(
        latest_id=Subquery(latest_batch_subquery.values('id')[:1])
    ).values_list('latest_id', flat=True)

    # Obtener los lotes finales
    return Batch.objects.filter(id__in=latest_batch_ids).order_by('expiration_date').values('id', 'batch_number',
                                                                                            'remaining_quantity',
                                                                                            'expiration_date')


def modal_picking_create(request):
    if request.method == 'GET':
        guides_ids = sorted(json.loads(request.GET.get('guides', '[]')))
        vehicle_id = request.GET.get('vehicleID', '')
        modality = request.GET.get('modality', '')
        carrier_id = request.GET.get('carrierID', '')
        driver_id = request.GET.get('driverID', '')
        store_id = request.GET.get('storeID', '')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        formattime = my_date.strftime("%H:%M:%S")
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        unit_description = ''
        guide_numbers = []
        all_purchases_ids = []
        purchase_dict = []
        quantity_total = 0
        vehicle_obj = ''
        carrier_obj = ''
        driver_obj = ''
        if vehicle_id:
            vehicle_obj = Truck.objects.get(id=vehicle_id)
        if carrier_id:
            carrier_obj = Owner.objects.get(id=carrier_id)
        if driver_id:
            driver_obj = Driver.objects.get(id=driver_id)

        store_obj = SubsidiaryStore.objects.get(id=store_id)

        supplier_name = ''
        supplier_address = ''
        grouped_by_product = {}

        last_number = get_last_picking_number()

        if guides_ids:
            # Obtener las guías para acceder a contract_detail
            guides = Guide.objects.filter(id__in=guides_ids).select_related('contract_detail')
            
            # Obtener los bill_number de las compras asociadas a cada guía
            for guide in guides:
                if guide.contract_detail:
                    # Buscar las compras asociadas al contract_detail
                    contract_detail_purchases = guide.contract_detail.contractdetailpurchase_set.select_related('purchase')
                    for cdp in contract_detail_purchases:
                        if cdp.purchase and cdp.purchase.bill_number:
                            all_purchases_ids.append(cdp.purchase.bill_number)
            
            guide_details = GuideDetail.objects.filter(
                guide_id__in=guides_ids
            ).select_related('product', 'unit', 'batch')

            for detail in guide_details:
                quantity_minimum = decimal.Decimal(0.00)
                product = detail.product
                product_id = product.id
                quantity = float(detail.quantity)
                weight_kg = product.weight / 1000
                weight = quantity * float(weight_kg)
                product_detail_set = ProductDetail.objects.filter(unit__description='CAJA', product=detail.product)
                if product_detail_set.exists():
                    product_detail_obj = product_detail_set.last()
                    quantity_minimum = product_detail_obj.quantity_minimum

                if product_id not in grouped_by_product:
                    grouped_by_product[product_id] = {
                        'product_id': product.id,
                        'product_code': product.code,
                        'product_name': product.name,
                        'details': [],
                        'total_quantity': 0.0,
                        'total_weight': 0.0
                    }
                if quantity_minimum > 0:
                    quantity_box = int(detail.quantity / quantity_minimum)
                    quantity_und = round(detail.quantity - (quantity_box * quantity_minimum))
                else:
                    quantity_box = decimal.Decimal(0.00)
                    quantity_und = round(detail.quantity)
                grouped_by_product[product_id]['details'].append({
                    'quantity': str(round(detail.quantity)),
                    'quantity_box': str(quantity_box),
                    'quantity_unit': str(quantity_und),
                    'unit': detail.unit.name,
                    'unit_id': detail.unit.id,
                    'batch': detail.batch.batch_number if detail.batch else None,
                    'batch_id': detail.batch.id if detail.batch else None,
                    'weight': str(round(detail.quantity * weight_kg)),
                    'guide_detail': detail.id,
                    'guide': detail.guide.id
                })

                grouped_by_product[product_id]['total_quantity'] += quantity
                grouped_by_product[product_id]['total_weight'] += weight

                for p_data in grouped_by_product.values():
                    p_data['total_quantity'] = round(p_data['total_quantity'], 0)
                    p_data['total_weight'] = round(p_data['total_weight'], 0)
            t = loader.get_template('comercial/modal_picking_create.html')

            products = Product.objects.filter(is_enabled=True)
            product_list = []

            for product in products:
                batches_list = list(get_latest_batches_for_product(product))

                units = ProductDetail.objects.filter(
                    product=product,
                    is_enabled=True
                ).select_related('unit').values('unit__id', 'unit__description')

                units_list = list(units)

                product_data = {
                    'id': product.id,
                    'name': product.name,
                    'weight': product.weight / 1000,
                    'batches': batches_list,
                    'units': units_list
                }
                product_list.append(product_data)

            # Convertir los campos a JSON con los Decimals como strings
            for product in product_list:
                product['batches'] = json.dumps(product['batches'], ensure_ascii=False, default=str)
                product['units'] = json.dumps(product['units'], ensure_ascii=False)

            c = ({
                'formatdate': formatdate,
                'formattime': formattime,
                'supplier_name': supplier_name,
                'supplier_address': supplier_address,
                'detail_purchase': purchase_dict,
                'oc_ids': all_purchases_ids,
                'guide_numbers': ', '.join(guide_numbers),
                'unit_name': unit_description,
                'user_obj': user_obj,
                'vehicle_obj': vehicle_obj,
                'carrier_obj': carrier_obj,
                'driver_obj': driver_obj,
                'store_obj': store_obj,
                'modality': modality,
                'product_set': product_list,
                'last_picking_number': str(last_number).zfill(6),
                'details_product': grouped_by_product,
                'quantity_total': round(quantity_total, 0),
            })
            return JsonResponse({
                'form': t.render(c, request),
            })


def decimal_to_str(obj):
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError(f'Type {type(obj)} not serializable')


def modal_phase(request):
    if request.method == 'GET':
        order_id = request.GET.get('order', '')
        phase = request.GET.get('phase', '')
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")

        phase_map = {
            'C': 'Compromiso',
            'D': 'De Vengado',
            'G': 'Girado',
        }

        try:
            order_obj = Order.objects.get(id=order_id)
        except (Order.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Orden no encontrada'}, status=HTTPStatus.BAD_REQUEST)

        # Obtener datos adicionales de la guía relacionada
        bill_info = {
            'serial': '-',
            'correlative': '-',
            'amount': '-',
            'order_buy': '-',
            'cod_siaf': '-'
        }
        
        # Buscar la guía relacionada a través del contract_detail
        try:
            # Obtener el contract_detail relacionado con la orden
            contract_detail = order_obj.contractdetail_set.first()
            if contract_detail:
                # Obtener la guía más reciente relacionada al contract_detail
                guide_obj = contract_detail.guide_set.last()
                order_obj = contract_detail.order
                if guide_obj:
                    # bill_info['serial'] = guide_obj.serial or '-'
                    # bill_info['correlative'] = guide_obj.correlative or '-'
                    bill_info['order_buy'] = guide_obj.order_buy or '-'
                    bill_info['cod_siaf'] = guide_obj.cod_siaf or '-'
                if order_obj:
                    bill_info['serial'] = order_obj.serial or '-'
                    bill_info['correlative'] = order_obj.correlative or '-'
                    bill_info['total_order'] = f"S/ {order_obj.total:,.2f}" or '-'
                # Obtener el monto de la factura desde la compra relacionada
                purchase_obj = contract_detail.contractdetailpurchase_set.last()
                if purchase_obj and purchase_obj.purchase:
                    bill_info['amount'] = f"S/ {purchase_obj.purchase.total():,.2f}"
        except Exception as e:
            print(e)
            # Si hay algún error, mantener los valores por defecto
            pass

        # Obtener el cliente de la orden
        client_obj = None
        cod_client = None
        if hasattr(order_obj, 'client') and order_obj.client:
            client_obj = order_obj.client
            cod_client = order_obj.client.cod_siaf

        tpl = loader.get_template('comercial/modal_phases.html')
        context = ({
            'order_obj': order_obj,
            'cod_client': cod_client,
            'client_obj': client_obj,
            'phase_code': phase,
            'phase_description': phase_map[phase],
            'formatdate': formatdate,
            'bill_info': bill_info,
        })
        return JsonResponse({
            'success': True,
            'form': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def save_phase(request):
    if request.method == 'GET':
        order_id = request.GET.get('order', '')
        phase = request.GET.get('phase', '')
        phase_date = request.GET.get('phase_date', '')
        phase_field_map = {
            'C': 'phase_c',
            'D': 'phase_d',
            'G': 'phase_g',
        }
        try:
            order_obj = Order.objects.get(id=order_id)
            setattr(order_obj, phase_field_map[phase], phase_date)

            if phase == 'G':
                order_obj.total_payed = decimal.Decimal(request.GET.get('total_pay', ''))
                order_obj.total_retention = decimal.Decimal(request.GET.get('total_retention', ''))
                order_obj.total_warranty = decimal.Decimal(request.GET.get('total_warranty', ''))

            order_obj.save()
        except (Order.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Orden no encontrada'}, status=HTTPStatus.BAD_REQUEST)

        return JsonResponse({
            'success': True,
            'order_id': order_obj.id,
            'phase_date': phase_date,
            'phase': phase,
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def save_picking(request):
    if request.method == 'POST':
        carrier_id = request.POST.get('carrier_id', '')
        vehicle_id = request.POST.get('vehicle_id', '')
        modality = request.POST.get('modality', '')
        driver_id = request.POST.get('driver_id')
        emit_date = str(request.POST.get('emit_date'))
        emit_hour = request.POST.get('emit_hour')
        picking_number = get_last_picking_number()
        detail = json.loads(request.POST.get('detail', ''))
        detail_reserve = json.loads(request.POST.get('products_reserve', ''))
        store_obj = SubsidiaryStore.objects.get(id=request.POST.get('store_id'))

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        carrier_obj = Owner.objects.get(id=int(carrier_id))
        vehicle_obj = Truck.objects.get(id=int(vehicle_id))
        driver_obj = Driver.objects.get(id=int(driver_id))

        picking_obj = Picking.objects.create(
            picking_number=picking_number,
            departure_date=emit_date,
            carrier=carrier_obj,
            vehicle=vehicle_obj,
            driver=driver_obj,
            modality_transport=modality,
            departure_time=emit_hour,
            subsidiary=subsidiary_obj
        )

        guides = set()

        for item in detail:
            product_id = int(item['product_id'])
            product_obj = Product.objects.get(id=product_id)

            for detail in item.get('productDetails', []):
                batch_obj = None
                batch = detail.get('batchID')
                unit_id = detail.get('unitID')
                guide_detail_id = detail.get('guideDetailID')
                guide_detail_obj = GuideDetail.objects.get(id=guide_detail_id)
                unit_obj = Unit.objects.get(id=int(unit_id))
                if batch:
                    batch_obj = Batch.objects.get(id=batch)
                quantity = decimal.Decimal(detail.get('quantity', 0))
                weight = detail.get('weight', 0)

                PickingDetail.objects.create(
                    picking=picking_obj,
                    product=product_obj,
                    batch=batch_obj,
                    quantity=quantity,
                    weight=weight,
                    unit=unit_obj,
                    detail_type='M'
                )
                PickingGuide.objects.create(guide_detail=guide_detail_obj, guide=guide_detail_obj.guide,
                                            picking=picking_obj)

                product_store_id = ProductStore.objects.filter(product=product_obj,
                                                               subsidiary_store=store_obj).last().id

                kardex_ouput(product_store_id, decimal.Decimal(quantity), guide_detail_obj=guide_detail_obj, type_document='09',
                             type_operation='01', batch_obj=batch_obj)

                guide = guide_detail_obj.guide
                guide.status = '2'
                guide.save()
                guides.add(guide.id)

        for d in detail_reserve:
            product_id = int(d['product_id'])
            batch_id = int(d['batch_id'])
            quantity = decimal.Decimal(d['quantity'])
            weight = int(d['weight'])
            batch_obj = None
            product_obj = Product.objects.get(id=product_id)
            unit_obj = Unit.objects.get(id=int(1))  # UNIT
            if batch_id:
                batch_obj = Batch.objects.get(id=batch_id)

            picking_detail_obj = PickingDetail.objects.create(
                picking=picking_obj,
                product=product_obj,
                batch=batch_obj,
                quantity=quantity,
                weight=weight,
                unit=unit_obj,
                detail_type='R'
            )

            product_store_id = ProductStore.objects.filter(product=product_obj,
                                                           subsidiary_store=store_obj).last().id

            kardex_ouput(product_store_id, quantity, picking_detail=picking_detail_obj, type_document='00',
                         type_operation='99', batch_obj=batch_obj)

        return JsonResponse({
            'message': 'Picking guardado correctamente',
            'guides': list(guides)
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_picking_with_guide(request):
    if request.method == 'GET':
        picking_set = Picking.objects.filter(status__in=['P', 'R']).order_by('-id')
        picking_dict = []

        for b in picking_set:

            rowspan = b.pickingdetail_set.all().count()

            if b.pickingdetail_set.count() == 0:
                rowspan = 1

            item_picking = {
                'id': b.id,
                'picking_number': str(b.picking_number).zfill(4),
                'departure_date': b.departure_date,
                'arrival_date': b.arrival_date,
                'status': b.status,
                'type': b.type,
                'weight': b.weight,
                'vehicle': b.vehicle,
                'subsidiary': b.subsidiary,
                'observation': b.observation,
                'modality_transport': b.modality_transport,
                'modality_transport_text': b.get_modality_transport_display(),
                'carrier': b.carrier.name,
                'departure_time': b.departure_time,
                'driver': b.driver.names,
                'picking_detail': [],
                'row_count': rowspan
            }
            for d in b.pickingdetail_set.all():
                item_detail = {
                    'id': d.id,
                    'product': d.product.name,
                    'quantity': str(round(d.quantity, 2)),
                    'unit': d.unit.description,
                    'batch': d.batch,
                    'batch_number': d.batch.batch_number,
                    'weight': str(d.weight),
                    'type': d.detail_type,
                    'type_text': d.get_detail_type_display(),
                }
                item_picking.get('picking_detail').append(item_detail)
            picking_dict.append(item_picking)

        t = loader.get_template('comercial/picking_list_guides.html')
        c = ({
            'picking_dict': picking_dict,
        })
        return JsonResponse({
            'grid': t.render(c, request),
            'success': True,
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion'}, status=HTTPStatus.BAD_REQUEST)


def get_guide(request):
    if request.method == 'GET':
        picking_id = request.GET.get('picking', '')
        picking_obj = Picking.objects.get(pk=int(picking_id))
        picking_guide_set = PickingGuide.objects.filter(picking=picking_obj)

        t = loader.get_template('comercial/get_guide_details.html')
        c = ({
            'picking_guide_set': picking_guide_set,
        })
        return JsonResponse({
            'success': True,
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)