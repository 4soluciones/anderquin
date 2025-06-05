import decimal
from http import HTTPStatus
from django.db.models import Q, Max, F, Prefetch, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.views.generic import View, TemplateView, UpdateView, CreateView
from django.views.decorators.csrf import csrf_exempt
from .models import *
from apps.hrm.models import Subsidiary, Employee, District, Department, Province
from django.http import JsonResponse
from .forms import *
from django.urls import reverse_lazy
from apps.sales.models import Product, SubsidiaryStore, ProductStore, ProductDetail, ProductSubcategory, \
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


# ----------------------------------------Programming-------------------------------


class ProgrammingCreate(CreateView):
    model = Programming
    form_class = FormProgramming
    template_name = 'comercial/programming_list.html'
    success_url = reverse_lazy('comercial:programming_list')


class ProgrammingList(View):
    model = Programming
    form_class = FormProgramming
    template_name = 'comercial/programming_create.html'

    def get_context_data(self, **kwargs):
        user_id = self.request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        context = {
            'subsidiaries': Subsidiary.objects.exclude(name=subsidiary_obj.name),
            'employees': Employee.objects.all(),
            'trucks': Truck.objects.all(),
            'towings': Towing.objects.all(),
            'choices_status': Programming._meta.get_field('status').choices,
            'form': self.form_class,
            'current_date': formatdate,
            'subsidiary_origin': subsidiary_obj,
            'programmings': get_programmings(need_rendering=False, subsidiary_obj=subsidiary_obj)
        }
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


@csrf_exempt
def new_programming(request):
    if request.method == 'POST':

        weight = 0
        if len(request.POST.get('weight', 0)) > 0:
            weight = float(request.POST.get('weight', 0))

        truck = request.POST.get('truck', '')
        departure_date = request.POST.get('departure_date')

        arrival_date = None
        if len(request.POST.get('arrival_date', '')):
            arrival_date = request.POST.get('arrival_date', '')

        status = request.POST.get('status', '')
        towing = request.POST.get('towing', '')
        subsidiary_origin = request.POST.get('origin', '')
        subsidiary_destiny = request.POST.get('destiny', '')
        observation = request.POST.get('observation', '')
        order = request.POST.get('order', '')
        km_initial = request.POST.get('km_initial', '')
        km_ending = request.POST.get('km_ending', '')
        pilot = request.POST.get('pilot', '')
        copilot = request.POST.get('copilot', '')

        pilot_obj = Employee.objects.get(pk=int(pilot))

        if len(truck) > 0:
            truck_obj = Truck.objects.get(id=truck)
            towing_obj = None
            if len(towing) > 0:
                towing_obj = Towing.objects.get(id=towing)
            subsidiary_origin_obj = Subsidiary.objects.get(id=subsidiary_origin)
            subsidiary_destiny_obj = Subsidiary.objects.get(id=subsidiary_destiny)
            data_programming = {
                'departure_date': departure_date,
                'arrival_date': arrival_date,
                'status': status,
                'type': 'G',
                'weight': weight,
                'truck': truck_obj,
                'towing': towing_obj,
                'subsidiary': subsidiary_origin_obj,
                'order': order,
                'km_initial': km_initial,
                'km_ending': km_ending,
                'observation': observation,
            }
            programming_obj = Programming.objects.create(**data_programming)
            programming_obj.save()

            set_employee_pilot_obj = SetEmployee(
                programming=programming_obj,
                employee=pilot_obj,
                function='P',
            )
            set_employee_pilot_obj.save()

            if copilot != '0':
                copilot_obj = Employee.objects.get(pk=int(copilot))
                set_employee_copilot_obj = SetEmployee(
                    programming=programming_obj,
                    employee=copilot_obj,
                    function='C',
                )
                set_employee_copilot_obj.save()

            route_origin_obj = Route(
                programming=programming_obj,
                subsidiary=subsidiary_origin_obj,
                type='O',
            )
            route_origin_obj.save()

            route_destiny_obj = Route(
                programming=programming_obj,
                subsidiary=subsidiary_destiny_obj,
                type='D',
            )
            route_destiny_obj.save()

            user_id = request.user.id
            user_obj = User.objects.get(pk=int(user_id))
            subsidiary_obj = get_subsidiary_by_user(user_obj)

            return JsonResponse({
                'success': True,
                'message': 'La Programacion se guardo correctamente.',
                'grid': get_programmings(need_rendering=True, subsidiary_obj=subsidiary_obj),
            })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_programming(request):
    if request.method == 'GET':
        id_programming = request.GET.get('programming', '')
        programming_obj = Programming.objects.get(id=int(id_programming))
        tpl = loader.get_template('comercial/programming_form.html')
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        print('origin')
        print(programming_obj.route_set.all())
        print(programming_obj.route_set.filter(type='O'))
        print(programming_obj.route_set.filter(type='O').first())
        print(programming_obj.setemployee_set.filter(function='P').first())

        context = ({
            'programming_obj': programming_obj,
            'origin': programming_obj.route_set.filter(type='O').first(),
            'destiny': programming_obj.route_set.filter(type='D').first(),
            'pilot': programming_obj.setemployee_set.filter(function='P').first(),
            'copilot': programming_obj.setemployee_set.filter(function='C').first(),
            'subsidiary_origin': subsidiary_obj,
            'subsidiaries': Subsidiary.objects.all(),
            'employees': Employee.objects.all(),
            'trucks': Truck.objects.all(),
            'towings': Towing.objects.all(),
            'choices_status': Programming._meta.get_field('status').choices,
        })

        return JsonResponse({
            'grid': tpl.render(context),
        }, status=HTTPStatus.OK)


def update_programming(request):
    print(request.method)
    data = {}
    if request.method == 'POST':
        id_programming = request.POST.get('programming', '')
        programming_obj = Programming.objects.get(id=int(id_programming))

        id_subsidiary_origin = request.POST.get('origin', '')
        id_subsidiary_destiny = request.POST.get('destiny', '')
        id_pilot = request.POST.get('pilot', '')
        id_copilot = request.POST.get('copilot', '')
        id_truck = request.POST.get('truck', '')
        id_towing = request.POST.get('towing', '')
        departure_date = request.POST.get('departure_date')
        arrival_date = request.POST.get('arrival_date', '')
        status = request.POST.get('status', '')
        order = request.POST.get('order', '')
        km_initial = request.POST.get('km_initial', '')
        km_ending = request.POST.get('km_ending', '')
        weight = request.POST.get('weight', 0)
        observation = request.POST.get('observation', '')

        set_employee_obj = SetEmployee.objects.filter(programming=programming_obj)
        old_pilot_obj = set_employee_obj.filter(function='P').first()
        old_copilot_obj = set_employee_obj.filter(function='C').first()

        new_pilot_obj = Employee.objects.get(pk=int(id_pilot))
        if new_pilot_obj != old_pilot_obj:
            set_employee_obj.filter(function='P').delete()
            SetEmployee(employee=new_pilot_obj, function='P', programming=programming_obj).save()

        if id_copilot != '0':
            new_copilot_obj = Employee.objects.get(pk=int(id_copilot))
            if new_copilot_obj != old_copilot_obj:
                set_employee_obj.filter(function='C').delete()
                SetEmployee(employee=new_copilot_obj, function='C', programming=programming_obj).save()

        if len(id_truck) > 0:
            truck_obj = Truck.objects.get(id=int(id_truck))
            programming_obj.truck = truck_obj

        if len(id_towing) > 0:
            towing_obj = Towing.objects.get(id=int(id_towing))
            programming_obj.towing = towing_obj

        new_subsidiary_origin_obj = None
        new_subsidiary_destiny_obj = None

        if len(id_subsidiary_origin) > 0:
            new_subsidiary_origin_obj = Subsidiary.objects.get(pk=int(id_subsidiary_origin))
        if len(id_subsidiary_destiny) > 0:
            new_subsidiary_destiny_obj = Subsidiary.objects.get(pk=int(id_subsidiary_destiny))

        routes_obj = Route.objects.filter(programming=programming_obj)
        old_subsidiary_origin_obj = routes_obj.filter(type='O').first()
        old_subsidiary_destiny_obj = routes_obj.filter(type='D').first()

        if new_subsidiary_origin_obj != old_subsidiary_origin_obj:
            routes_obj.filter(type='O').delete()
            Route(subsidiary=new_subsidiary_origin_obj, type='O', programming=programming_obj).save()

        if new_subsidiary_destiny_obj != old_subsidiary_destiny_obj:
            routes_obj.filter(type='D').delete()
            Route(subsidiary=new_subsidiary_destiny_obj, type='D', programming=programming_obj).save()

        programming_obj.weight = float(weight)
        programming_obj.status = status
        programming_obj.departure_date = departure_date
        programming_obj.arrival_date = arrival_date
        programming_obj.km_initial = km_initial
        programming_obj.km_ending = km_ending

        if len(order) > 0:
            programming_obj.order = int(order)
        programming_obj.observation = observation
        programming_obj.save()

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        return JsonResponse({
            'success': True,
            'message': 'La Programacion se guardo correctamente.',
            'grid': get_programmings(need_rendering=True, subsidiary_obj=subsidiary_obj),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_programmings(need_rendering, subsidiary_obj=None):
    my_date = datetime.now()
    formatdate = my_date.strftime("%Y-%m-%d")
    if subsidiary_obj is None:
        # programmings = Programming.objects.all().order_by('id')
        programmings = Programming.objects.filter(departure_date__gte=formatdate, status__in=['P', 'R']).order_by('id')
    else:
        # programmings = Programming.objects.filter(subsidiary=subsidiary_obj).order_by('id')
        programmings = Programming.objects.filter(subsidiary=subsidiary_obj, departure_date__gte=formatdate,
                                                  status__in=['P', 'R']).order_by('id')
    print(programmings)
    # programmings = Programming.objects.filter(departure_date__gte=formatdate, status__in=['P', 'R']).order_by('id')
    if need_rendering:
        tpl = loader.get_template('comercial/programming_list.html')
        context = ({'programmings': programmings, })
        return tpl.render(context)
    return programmings


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


def get_programming_guide(request):
    if request.method == 'GET':
        id_programming = request.GET.get('programming', '')
        programming_obj = Programming.objects.get(id=int(id_programming))
        pilot = programming_obj.setemployee_set.filter(function='P').first().employee
        name = pilot.names + ' ' + pilot.paternal_last_name

        # print(programming_obj.route_set.filter(type='O').first().subsidiary.name)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()
        products = Product.objects.filter(productstore__subsidiary_store=subsidiary_store_obj)

        tpl = loader.get_template('comercial/detail_guide.html')
        context = ({
            'products': products,
            'type': GuideDetail._meta.get_field('type').choices,
        })
        return JsonResponse({
            'origin': programming_obj.route_set.filter(type='O').first().subsidiary.name,
            'destiny': programming_obj.route_set.filter(type='D').first().subsidiary.name,
            'pilot': name,
            'departure_date': programming_obj.departure_date,
            'products_grids': tpl.render(context),
            'license_plate': programming_obj.truck.license_plate,
            'truck_brand': programming_obj.truck.truck_model.truck_brand.name,
            'truck_serial': programming_obj.truck.serial,
            'license': programming_obj.setemployee_set.filter(function='P').first().employee.n_license,
            'license_type': programming_obj.setemployee_set.filter(
                function='P').first().employee.get_license_type_display(),

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


# def create_guide(request):
#     if request.method == 'GET':
#         guides_request = request.GET.get('guides', '')
#         data_guides = json.loads(guides_request)
#         print(data_guides)
#         user_id = request.user.id
#         user_obj = User.objects.get(pk=int(user_id))
#         serial = str(data_guides["Serial"])
#         code = str(data_guides["Code"])
#         minimal_cost = float(data_guides["Minimal_cost"])
#         programming = int(data_guides["Programming"])
#         programming_obj = Programming.objects.get(pk=programming)
#
#         new_guide = {
#             'serial': serial,
#             'code': code,
#             # 'minimal_cost': minimal_cost,
#             'user': user_obj,
#             'programming': programming_obj,
#         }
#         guide_obj = Guide.objects.create(**new_guide)
#         guide_obj.save()
#
#         for detail in data_guides['Details']:
#             quantity = int(detail['Quantity'])
#
#             # recuperamos del producto
#             product_id = int(detail['Product'])
#             product_obj = Product.objects.get(id=product_id)
#
#             # recuperamos la unidad
#             unit_id = int(detail['Unit'])
#             unit_obj = Unit.objects.get(id=unit_id)
#             _type = detail["type"]
#             new_detail_guide = {
#                 'guide': guide_obj,
#                 'product': product_obj,
#                 'quantity': quantity,
#                 'unit_measure': unit_obj,
#                 'type': _type,
#
#             }
#             new_detail_guide_obj = GuideDetail.objects.create(**new_detail_guide)
#             new_detail_guide_obj.save()
#
#             # recuperamos del almacen
#             store_id = int(detail['Store'])
#
#             kardex_ouput(store_id, quantity, guide_detail_obj=new_detail_guide_obj)
#         return JsonResponse({
#             'message': 'Se guardo la guia correctamente.',
#             'programming': programming_obj.id,
#             'guide': guide_obj.id
#         }, status=HTTPStatus.OK)


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


def report_guides_by_plate_grid(request):
    if request.method == 'POST':
        start_date = request.POST.get('start-date', '')
        end_date = request.POST.get('end-date', '')
        truck_plate = request.POST.get('plate', '')

        programmings_set = Programming.objects.filter(status__in=['F'], departure_date__range=(start_date, end_date),
                                                      guide__isnull=False, truck=truck_plate).order_by('departure_date')

        return JsonResponse({
            'grid': get_dict_programming_guides_queries(programmings_set),
        }, status=HTTPStatus.OK)


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


def guide_by_programming(request):
    if request.method == 'GET':
        id_programming = request.GET.get('programming', '')
        programming_obj = Programming.objects.get(id=int(id_programming))
        guide_obj = Guide.objects.filter(programming=programming_obj).first()
        details = GuideDetail.objects.filter(guide=guide_obj)

        tpl = loader.get_template('comercial/guide_detail_list.html')
        context = ({'guide': guide_obj, 'details': details})
        return JsonResponse({
            # 'message': 'guias recuperadas',
            'grid': tpl.render(context),
        }, status=HTTPStatus.OK)


def programmings_by_date(request):
    if request.method == 'GET':
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        programmings = Programming.objects.filter(status__in=['F'], departure_date__range=(start_date, end_date),
                                                  guide__isnull=False).order_by('id')

        tpl = loader.get_template('comercial/guide_detail_programming_list.html')
        context = ({'programmings': programmings})
        return JsonResponse({
            'grid': tpl.render(context),
        }, status=HTTPStatus.OK)


def programming_receive_by_sucursal(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        routes = Route.objects.filter(type='D', subsidiary=subsidiary_obj)
        # programmings = Programming.objects.filter(status__in=['P'], guide__isnull=False, route__in=routes).order_by('id')
        programmings = Programming.objects.filter(status__in=['P'], route__in=routes).order_by('id')

        status_obj = Programming._meta.get_field('status').choices
        return render(request, 'comercial/programming_receive.html', {
            'programmings': programmings,
            'choices_status': status_obj,

        })


def programming_receive_by_sucursal_detail_guide(request):
    if request.method == 'GET':
        id_programming = request.GET.get('programming', '')
        programming_obj = Programming.objects.get(id=int(id_programming))
        guide_obj = Guide.objects.filter(programming=programming_obj).first()
        details = GuideDetail.objects.filter(guide=guide_obj)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiaries_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj)
        # product_store_obj = ProductStore.objects.get(subsidiary_store=subsidiaries_store_obj)

        tpl = loader.get_template('comercial/programming_receive_detail.html')
        context = ({
            'guide': guide_obj,
            'details': details,
            'subsidiaries_store': subsidiaries_store_obj,

        })

        return JsonResponse({
            'message': 'guias recuperadas',
            'grid': tpl.render(context),
        }, status=HTTPStatus.OK)


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


def create_output_transfer(request):
    if request.method == 'GET':
        output_request = request.GET.get('transfer')
        data_transfer = json.loads(output_request)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        document_number = str(data_transfer["Document"])
        total = decimal.Decimal((data_transfer["Total"]).replace(',', '.'))
        document_type_attached = str(data_transfer["DocumentTypeAttached"])
        motive = int(data_transfer["Motive"])
        observation = str(data_transfer["Observation"])
        # Outputs: 1, 3, 6, 7
        # Transfers: 4
        a = [1, 3, 4, 6, 7]
        if motive not in a:
            data = {'error': "solo se permite traspase entre almacenes de la misma sede y/o salidas permitidas."}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        motive_obj = GuideMotive.objects.get(id=motive)
        origin = int(data_transfer["Origin"])
        origin_obj = SubsidiaryStore.objects.get(id=origin)

        destiny = int(data_transfer["Destiny"])
        destiny_obj = None
        if destiny != 0:
            destiny_obj = SubsidiaryStore.objects.get(id=destiny)
        if motive == 4 and destiny_obj is None:
            data = {'error': "no selecciono almacen destino."}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        function = 'S'
        status = '1'  # En transito
        if motive != 4:  # if is not transfer
            function = 'A'
            status = '5'  # Extraido

        new_guide_obj = Guide(
            serial=subsidiary_obj.serial,
            document_number=document_number,
            document_type_attached=document_type_attached,
            # minimal_cost=total,
            observation=observation.strip(),
            user=user_obj,
            guide_motive=motive_obj,
            status=status,
            subsidiary=subsidiary_obj,
        )
        new_guide_obj.save()

        new_origin_route_obj = Route(
            guide=new_guide_obj,
            subsidiary_store=origin_obj,
            type='O',
        )
        new_origin_route_obj.save()

        if destiny_obj is not None:
            new_destiny_route_obj = Route(
                guide=new_guide_obj,
                subsidiary_store=destiny_obj,
                type='D',
            )
            new_destiny_route_obj.save()

        new_guide_employee_obj = GuideEmployee(
            guide=new_guide_obj,
            user=user_obj,
            function=function,
        )
        new_guide_employee_obj.save()

        for details in data_transfer['Details']:
            product_id = int(details["Product"])
            product_store_id = int(details["ProductStore"])
            unit_id = int(details["Unit"])
            quantity_request = decimal.Decimal(details["Quantity"])
            price = decimal.Decimal(details["Price"])

            product_obj = Product.objects.get(id=product_id)
            unit_obj = Unit.objects.get(id=unit_id)

            new_guide_detail_obj = GuideDetail(
                guide=new_guide_obj,
                product=product_obj,
                quantity_request=quantity_request,
                quantity_sent=quantity_request,
                quantity=quantity_request,
                unit_measure=unit_obj,
            )
            new_guide_detail_obj.save()

            if motive != 4:
                product_store_obj = ProductStore.objects.get(id=product_store_id)
                # kardex_ouput(product_store_obj.id, quantity_request, guide_detail_obj=new_guide_detail_obj)

        return JsonResponse({
            'message': 'La operación se Realizo correctamente.',
            'guide_id': new_guide_obj.id,
        }, status=HTTPStatus.OK)


def output_change_status(request):
    if request.method == 'GET':
        guide_id = request.GET.get('pk', '')
        status_id = request.GET.get('status', '')
        guide_obj = Guide.objects.get(id=int(guide_id))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        if status_id == '2':  # Approve
            guide_obj.status = status_id
            guide_obj.save()
            new_guide_employee_obj = GuideEmployee(
                guide=guide_obj,
                user=user_obj,
                function='A',
            )
            new_guide_employee_obj.save()

        elif status_id == '4':  # Cancel
            guide_obj.status = status_id
            guide_obj.save()
            new_guide_employee_obj = GuideEmployee(
                guide=guide_obj,
                user=user_obj,
                function='C',
            )
            new_guide_employee_obj.save()

        return JsonResponse({
            'message': 'Se cambio el estado correctamente.',
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


def create_input_transfer(request):
    if request.method == 'GET':
        production_request = request.GET.get('transfer')
        data_transfer = json.loads(production_request)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        document_number = str(data_transfer["Document"])
        total = decimal.Decimal((data_transfer["Total"]).replace(',', '.'))
        document_type_attached = str(data_transfer["DocumentTypeAttached"])
        motive = int(data_transfer["Motive"])
        # if motive != 4:
        #     data = {'error': "solo se permite traspase entre almacenes de la misma sede."}
        #     response = JsonResponse(data)
        #     response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        #     return response
        motive_obj = GuideMotive.objects.get(id=motive)
        destiny = int(data_transfer["Destiny"])
        destiny_obj = SubsidiaryStore.objects.get(id=destiny)
        observation = str(data_transfer["Observation"])

        new_guide_obj = Guide(
            serial=subsidiary_obj.serial,
            document_number=document_number,
            document_type_attached=document_type_attached,
            # minimal_cost=total,
            observation=observation.strip(),
            user=user_obj,
            guide_motive=motive_obj,
            status='2',
            subsidiary=subsidiary_obj,
        )
        new_guide_obj.save()

        new_destiny_route_obj = Route(
            guide=new_guide_obj,
            subsidiary_store=destiny_obj,
            type='D',
        )
        new_destiny_route_obj.save()

        new_guide_employee_obj = GuideEmployee(
            guide=new_guide_obj,
            user=user_obj,
            function='A',
        )
        new_guide_employee_obj.save()

        for details in data_transfer['Details']:
            product_id = int(details["Product"])
            unit_id = int(details["Unit"])
            quantity = decimal.Decimal(details["Quantity"])
            price = decimal.Decimal(details["Price"])

            product_obj = Product.objects.get(id=product_id)
            unit_obj = Unit.objects.get(id=unit_id)

            new_guide_detail_obj = GuideDetail(
                guide=new_guide_obj,
                product=product_obj,
                quantity=quantity,
                unit_measure=unit_obj,
            )
            new_guide_detail_obj.save()

            product_store_obj = ProductStore.objects.filter(product=product_obj, subsidiary_store=destiny_obj).last()
            if product_store_obj:
                kardex_input(product_store_obj.id, quantity, price, guide_detail_obj=new_guide_detail_obj)
            else:
                product_store_obj = ProductStore(product=product_obj, subsidiary_store=destiny_obj, stock=quantity)
                product_store_obj.save()
                kardex_initial(product_store_obj, stock=quantity, price_unit=price,
                               guide_detail_obj=new_guide_detail_obj)

        return JsonResponse({
            'message': 'La operación se Realizo correctamente.',
            'guide_id': new_guide_obj.id,

        }, status=HTTPStatus.OK)


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


def new_input_from_output(request):
    if request.method == 'GET':
        transfer_request = request.GET.get('transfer', '')
        data = json.loads(transfer_request)

        output_guide_id = int(data['Guide'])
        output_guide_obj = Guide.objects.get(pk=output_guide_id)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)

        observation = str(data["Observation"])

        subsidiary_store_destiny_obj = output_guide_obj.get_destiny()
        subsidiary_store_origin_obj = output_guide_obj.get_origin()
        motive_obj = GuideMotive.objects.get(id=15)  # transfer

        # register new guide
        input_guide_obj = Guide(
            serial=subsidiary_store_destiny_obj.subsidiary.serial,
            document_number=output_guide_obj.get_serial(),
            document_type_attached=output_guide_obj.document_type_attached,
            # minimal_cost=total,
            observation=observation.strip(),
            user=user_obj,
            guide_motive=motive_obj,
            status='2',
            subsidiary=subsidiary_store_destiny_obj.subsidiary,
        )
        input_guide_obj.save()

        new_destiny_route_obj = Route(
            guide=input_guide_obj,
            subsidiary_store=subsidiary_store_destiny_obj,
            type='D',
        )
        new_destiny_route_obj.save()

        new_guide_employee_obj = GuideEmployee(
            guide=input_guide_obj,
            user=user_obj,
            function='A',
        )
        new_guide_employee_obj.save()
        # register new guide

        for detail in data['Details']:
            detail_id = int(detail["Detail"])
            quantity = decimal.Decimal(str(detail["Quantity"]).replace(',', '.'))

            if quantity > 0:

                # update output guide detail
                output_guide_detail_obj = GuideDetail.objects.get(id=detail_id)
                output_guide_detail_obj.quantity = quantity
                output_guide_detail_obj.save()
                # update output guide detail

                # output kardex
                output_product_store_obj = ProductStore.objects.get(
                    product=output_guide_detail_obj.product, subsidiary_store=subsidiary_store_origin_obj)
                # kardex_ouput(output_product_store_obj.id, quantity, guide_detail_obj=output_guide_detail_obj)
                # output kardex

                # register input guide detail
                input_guide_detail_obj = GuideDetail(
                    guide=input_guide_obj,
                    product=output_guide_detail_obj.product,
                    quantity=quantity,
                    unit_measure=output_guide_detail_obj.unit_measure,
                )
                input_guide_detail_obj.save()
                # register input guide detail

                # input kardex
                input_product_store_obj = ProductStore.objects.filter(
                    product=output_guide_detail_obj.product, subsidiary_store=subsidiary_store_destiny_obj).last()
                if input_product_store_obj:
                    kardex_input(input_product_store_obj.id,
                                 quantity,
                                 output_guide_detail_obj.product.calculate_minimum_price_sale(),
                                 guide_detail_obj=input_guide_detail_obj)
                else:
                    input_product_store_obj = ProductStore(product=output_guide_detail_obj.product,
                                                           subsidiary_store=subsidiary_store_destiny_obj,
                                                           stock=quantity)
                    input_product_store_obj.save()
                    kardex_initial(input_product_store_obj,
                                   stock=quantity,
                                   price_unit=output_guide_detail_obj.product.calculate_minimum_price_sale(),
                                   guide_detail_obj=input_guide_detail_obj)
                # input kardex
        output_guide_obj.status = '3'
        output_guide_obj.observation = observation
        output_guide_obj.save()

        new_guide_employee_obj = GuideEmployee(
            guide=output_guide_obj,
            user=user_obj,
            function='A',
        )
        new_guide_employee_obj.save()
        return JsonResponse({
            'message': 'La operación se Realizo correctamente.',
            'guide_id': input_guide_obj.id,
        }, status=HTTPStatus.OK)


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


def distribution_mobil_save(request):
    if request.method == 'GET':
        distribution_request = request.GET.get('distribution', '')
        data_distribution = json.loads(distribution_request)
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        date_distribution = (data_distribution["date_distribution"])
        id_truck = int(data_distribution["id_truck"])
        truck_obj = Truck.objects.get(id=id_truck)
        id_pilot = int(data_distribution["id_pilot"])
        guide = str(data_distribution["number_guide"])
        employee_obj = Employee.objects.get(id=id_pilot)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        subsidiary_store_obj = SubsidiaryStore.objects.filter(subsidiary=subsidiary_obj, category='V').first()
        new_distribution = {
            'truck': truck_obj,
            'pilot': employee_obj,
            'date_distribution': date_distribution,
            'subsidiary': subsidiary_obj,
            'user': user_obj,
            'guide_number': guide,
        }
        distribution_obj = DistributionMobil.objects.create(**new_distribution)
        distribution_obj.save()
        status = ''
        for detail in data_distribution['Details']:
            quantity = decimal.Decimal(detail['Quantity'])
            quantity_total = decimal.Decimal(detail['Quantity_total'])
            product_id = int(detail['Product'])
            type = str(detail['Type'])
            status = str(detail['Status'])
            product_obj = Product.objects.get(id=product_id)
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)

            new_detail_distribution = {
                'product': product_obj,
                'distribution_mobil': distribution_obj,
                'quantity': quantity_total,
                'unit': unit_obj,
                'type': type,
                'status': status,
            }
            new_detail_distribution = DistributionDetail.objects.create(**new_detail_distribution)
            new_detail_distribution.save()

            if quantity > 0 and type != 'V':
                product_store_obj = ProductStore.objects.get(product=product_obj,
                                                             subsidiary_store=subsidiary_store_obj)
                quantity_minimum_unit = calculate_minimum_unit(quantity, unit_obj, product_obj)
                # kardex_ouput(product_store_obj.id, quantity_minimum_unit,
                #              distribution_detail_obj=new_detail_distribution)

        return JsonResponse({
            'message': 'DISTRIBUCION REALIZADA.',
        }, status=HTTPStatus.OK)


def output_distribution_list(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    distribution_mobil = DistributionMobil.objects.filter(subsidiary=subsidiary_obj, status='P')
    return render(request, 'comercial/output_distribution_list.html', {
        'distribution_mobil': distribution_mobil
    })


def get_details_by_distributions_mobil(request):
    if request.method == 'GET':
        distribution_mobil_id = request.GET.get('ip', '')
        distribution_mobil_obj = DistributionMobil.objects.get(pk=int(distribution_mobil_id))
        details_distribution_mobil = DistributionDetail.objects.filter(
            distribution_mobil=distribution_mobil_obj
        ).select_related('product', 'unit')
        t = loader.get_template('comercial/table_details_output_distribution.html')
        c = ({
            'details': details_distribution_mobil,
        })
        return JsonResponse({
            'grid': t.render(c, request),
        }, status=HTTPStatus.OK)


def get_distribution_mobil_return(request):
    if request.method == 'GET':
        pk = int(request.GET.get('pk', ''))

        distribution_mobil_obj = DistributionMobil.objects.get(id=pk)
        if distribution_mobil_obj.status == 'F':
            return JsonResponse({
                'error': 'LA PROGRAMACION YA ESTA FINALIZADA, POR FAVOR SELECCIONE OTRA',
            })
        # distribution_mobil_detail = DistributionDetail.objects.filter(distribution_mobil=distribution_mobil_obj)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        product_obj = Product.objects.filter(productstore__subsidiary_store__subsidiary=subsidiary_obj,
                                             productstore__subsidiary_store__category='V')

        # product_serialized_obj = serializers.serialize('json', product)

        t = loader.get_template('comercial/distribution_mobil_return.html')
        c = ({
            'distribution_mobil': distribution_mobil_obj,
            'product': product_obj,
            'type': DistributionDetail._meta.get_field('type').choices,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
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


@csrf_exempt
def c_return_distribution_mobil_detail(request):
    if request.method == 'GET':
        _c_distribution_mobil = request.GET.get('c_distribution_mobil', '')
        _c_detail = json.loads(_c_distribution_mobil)
        _c_distribution_mobil_id = int(_c_detail["c_distribution_id"])
        _c_distribution_mobil_obj = DistributionMobil.objects.get(id=_c_distribution_mobil_id)

        if _c_distribution_mobil_obj.status == 'F':
            data = {'error': 'Reparto retornado.'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        for detail in _c_detail['c_detail']:
            _c_quantity = decimal.Decimal(detail['c_quantity'])
            _c_product_id = int(detail['c_product_id'])
            _c_product_obj = Product.objects.get(id=_c_product_id)
            _c_type_id = detail['c_type_id']
            _c_unit = detail['c_unit']
            _c_unit_obj = Unit.objects.get(name=str(_c_unit))
            _c_status = 'C'

            _c_new_detail_distribution = {
                'product': _c_product_obj,
                'distribution_mobil': _c_distribution_mobil_obj,
                'quantity': _c_quantity,
                'unit': _c_unit_obj,
                'status': _c_status,
                'type': _c_type_id,
            }
            _c_new_detail_distribution = DistributionDetail.objects.create(**_c_new_detail_distribution)
            _c_new_detail_distribution.save()
        _c_distribution_mobil_obj.status = 'F'
        _c_distribution_mobil_obj.save()
        return JsonResponse({
            'message': 'Productos retornados correctamente',

        }, status=HTTPStatus.OK)


def get_distribution_list(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        date_distribution = request.GET.get('_date', '')
        if date_distribution != '':

            distribution_mobil = DistributionMobil.objects.filter(
                subsidiary=subsidiary_obj, date_distribution=date_distribution).prefetch_related(
                Prefetch('distributiondetail_set')
            ).select_related('truck')
            tpl = loader.get_template('comercial/distribution_grid_list.html')
            context = ({
                'distribution_mobil': distribution_mobil,
            })
            return JsonResponse({
                'success': True,
                'grid': tpl.render(context),
            }, status=HTTPStatus.OK)
        else:
            my_date = datetime.now()
            date_now = my_date.strftime("%Y-%m-%d")
            # distribution_mobil_set = DistributionMobil.objects.annotate(id=Max('date_distribution')).filter(subsidiary=subsidiary_obj, date_distribution=F('max_date'))
            # if distribution_mobil_set.exists():
            #     date_now = distribution_mobil_set.first().date_distribution.strftime("%Y-%m-%d")
            return render(request, 'comercial/distribution_list.html', {
                'date_now': date_now,
            })


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


def get_quantity_last_distribution(request):
    if request.method == 'GET':
        id_pilot = request.GET.get('ip', '')
        employee_obj = Employee.objects.get(id=int(id_pilot))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        distribution_mobil = DistributionMobil.objects.filter(pilot=employee_obj, status='F',
                                                              subsidiary=subsidiary_obj).aggregate(Max('id'))
        if distribution_mobil['id__max'] is not None:
            truck = DistributionMobil.objects.get(id=distribution_mobil['id__max']).truck
            truck_obj = Truck.objects.get(license_plate=truck)

            list_distribution_last = DistributionDetail.objects.filter(status='C',
                                                                       distribution_mobil=distribution_mobil['id__max'])
            list_serialized_obj = serializers.serialize('json', list_distribution_last)
            if list_distribution_last.exists():
                t = loader.get_template('comercial/table_distribution_last.html')
                c = ({
                    'details': list_distribution_last,

                })
                return JsonResponse({
                    'message': True,
                    'truck': truck_obj.id,
                    'grid': t.render(c, request),
                    'list': list_serialized_obj,
                }, status=HTTPStatus.OK)
            else:
                return JsonResponse({
                    'truck': truck_obj.id,
                    'message': False,
                }, status=HTTPStatus.OK)
        else:
            return JsonResponse({
                'message': False,
            }, status=HTTPStatus.OK)
        # try:
        # except DistributionMobil.DoesNotExist:


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


def get_programming_by_license_plate(request):
    id_programming = request.GET.get('ip', '')
    programming_obj = Programming.objects.get(pk=int(id_programming))
    print(programming_obj)
    name = ''
    document = ''
    employee_obj = programming_obj.get_pilot()
    if employee_obj is not None:
        # name = employee_obj.full_name
        name = '{} {} {}'.format(employee_obj.names, employee_obj.paternal_last_name, employee_obj.maternal_last_name)
        document = employee_obj.document_number

    return JsonResponse({
        'employee_name': name,
        'employee_document': document,
    }, status=HTTPStatus.OK)


def get_distribution_query(request):
    if request.method == 'GET':
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        truck_set = Truck.objects.filter(distributionmobil__isnull=False).distinct('license_plate').order_by(
            'license_plate')
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        return render(request, 'comercial/distribution_queries.html', {
            'formatdate': formatdate,
            'subsidiary_obj': subsidiary_obj,
            'truck_set': truck_set,
        })
    elif request.method == 'POST':
        id_truck = int(request.POST.get('truck'))
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))

        if start_date == end_date:
            distribution_mobil_set = DistributionMobil.objects.filter(date_distribution=start_date,
                                                                      truck__id=id_truck).order_by('date_distribution')
        else:
            distribution_mobil_set = DistributionMobil.objects.filter(date_distribution__range=[start_date, end_date],
                                                                      truck__id=id_truck).order_by('date_distribution')
        if distribution_mobil_set:
            return JsonResponse({
                'grid': get_dict_distribution_queries(distribution_mobil_set, is_pdf=False),
            }, status=HTTPStatus.OK)
        else:
            data = {'error': "No hay operaciones registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response


def get_dict_distribution_queries(distribution_mobil_set, is_pdf=False):
    dictionary = []
    _sum_expenses = 0
    _sum_payments = 0
    for distribution in distribution_mobil_set:
        details = distribution.distributiondetail_set
        number_details = details.count()

        distribution_detail_set_count = distribution.distributiondetail_set.count()
        if number_details > 0:
            inputs = details.filter(status='D')
            outputs = details.filter(status='E')
            number_inputs = inputs.count()
            number_outputs = outputs.count()
            product_dict = {}
            for _input in inputs:
                _search_value = _input.product.id
                if _search_value in product_dict.keys():
                    _product = product_dict[_input.product.id]
                    _void = _product.get('i_void')
                    _filled = _product.get('i_filled')
                    _ruined = _product.get('i_ruined')
                    if _input.type == 'V':
                        product_dict[_input.product.id]['i_void'] = _void + _input.quantity
                    elif _input.type == 'L':
                        product_dict[_input.product.id]['i_filled'] = _filled + _input.quantity
                    elif _input.type == 'M':
                        product_dict[_input.product.id]['i_ruined'] = _ruined + _input.quantity
                else:
                    if _input.type == 'V':
                        product_dict[_input.product.id] = {'sold': 0, 'borrowed': 0,
                                                           'i_void': _input.quantity, 'i_filled': 0, 'i_ruined': 0,
                                                           'o_filled': 0, 'pk': _input.product.id,
                                                           'name': _input.product.name}
                    elif _input.type == 'L':
                        product_dict[_input.product.id] = {'sold': 0, 'borrowed': 0,
                                                           'i_void': 0, 'i_filled': _input.quantity, 'i_ruined': 0,
                                                           'o_filled': 0, 'pk': _input.product.id,
                                                           'name': _input.product.name}
                    elif _input.type == 'M':
                        product_dict[_input.product.id] = {'sold': 0, 'borrowed': 0,
                                                           'i_void': 0, 'i_filled': 0, 'i_ruined': _input.quantity,
                                                           'o_filled': 0, 'pk': _input.product.id,
                                                           'name': _input.product.name}
            for _output in outputs:
                _search_value = _output.product.id
                if _search_value in product_dict.keys():
                    _product = product_dict[_output.product.id]
                    _filled = _product.get('o_filled')
                    if _output.type == 'L':
                        product_dict[_output.product.id]['o_filled'] = _filled + _output.quantity
                else:
                    if _output.type == 'L':
                        product_dict[_output.product.id] = {'sold': 0, 'borrowed': 0,
                                                            'i_void': 0, 'i_filled': 0, 'i_ruined': 0,
                                                            'o_filled': _output.quantity, 'pk': _output.product.id,
                                                            'name': _output.product.name}

            new = {
                'id': distribution.id,
                'truck': distribution.truck.license_plate,
                'date': distribution.date_distribution,
                'input_distribution_detail': [],
                'output_distribution_detail': [],
                'sales': [],
                'products': [],
                'status': distribution.get_status_display(),
                'subsidiary': distribution.subsidiary.name,
                'pilot': distribution.pilot,
                'details_count': distribution_detail_set_count,
                'number_inputs': number_inputs,
                'number_outputs': number_outputs,
                'number_products': 0,
                'height': 0,
                'rows': 0,
                'number_sales': 0,
                'number_order_details': 0,
                'number_expenses': 0,
                'number_payments': 0,
                'is_multi_detail': False,
                'is_multi_expenses': False,
                'is_multi_payments': False,
            }

            for d in DistributionDetail.objects.filter(distribution_mobil=distribution):
                distribution_detail = {
                    'id': d.id,
                    'status': d.get_status_display(),
                    'product': d.product.name,
                    'quantity': d.quantity,
                    'unit': d.unit.name,
                    'distribution_mobil': d.distribution_mobil.id,
                    'type': d.get_type_display(),
                }
                if d.status == 'D':
                    new.get('input_distribution_detail').append(distribution_detail)
                elif d.status == 'E':
                    new.get('output_distribution_detail').append(distribution_detail)

            dictionary.append(new)
            _sales = Order.objects.filter(distribution_mobil=distribution).exclude(type='E')
            number_sales = _sales.count()
            new['number_sales'] = number_sales

            for o in _sales:
                _order_detail = o.orderdetail_set.all()

                for _detail in _order_detail:
                    _search_value = _detail.product.id
                    if _search_value in product_dict.keys():
                        _product = product_dict[_detail.product.id]
                        _sold = _product.get('sold')
                        _borrowed = _product.get('borrowed')
                        if _detail.unit.name == 'B':
                            product_dict[_detail.product.id]['borrowed'] = _borrowed + _detail.quantity_sold
                        elif _detail.unit.name == 'G':
                            product_dict[_detail.product.id]['sold'] = _sold + _detail.quantity_sold

                    else:
                        if _detail.unit.name == 'B':
                            product_dict[_detail.product.id] = {'sold': 0, 'borrowed': _detail.quantity_sold,
                                                                'i_void': 0, 'i_filled': 0, 'i_ruined': 0,
                                                                'o_filled': 0, 'pk': _detail.product.id,
                                                                'name': _detail.product.name}
                        elif _detail.unit.name == 'G':
                            product_dict[_detail.product.id] = {'sold': _detail.quantity_sold, 'borrowed': 0,
                                                                'i_void': 0, 'i_filled': 0, 'i_ruined': 0,
                                                                'o_filled': 0, 'pk': _detail.product.id,
                                                                'name': _detail.product.name}

                _expenses = o.cashflow_set.filter(type='S')
                _payments = o.cashflow_set.filter(Q(type='E') | Q(type='D'))

                number_order_details = _order_detail.count()
                if number_order_details == 0:
                    number_order_details = 1
                else:
                    if number_order_details > 1 and new['is_multi_detail'] is False:
                        new['is_multi_detail'] = True
                number_expenses = _expenses.count()
                if number_expenses == 0:
                    number_expenses = 1
                else:
                    _expenses_set = _expenses.values('order').annotate(totals=Sum('total'))
                    _sum_expenses = _sum_expenses + _expenses_set[0].get('totals')
                    if number_expenses > 1 and new['is_multi_expenses'] is False:
                        new['is_multi_expenses'] = True
                number_payments = _payments.count()
                if number_payments == 0:
                    number_payments = 1
                else:
                    _payments_set = _payments.values('order').annotate(totals=Sum('total'))
                    _sum_payments = _sum_payments + _payments_set[0].get('totals')
                    if number_payments > 1 and new['is_multi_payments'] is False:
                        new['is_multi_payments'] = True

                if (number_order_details >= number_expenses) and (number_order_details >= number_payments):
                    tbl2_height = number_order_details
                elif (number_expenses >= number_order_details) and (number_expenses >= number_payments):
                    tbl2_height = number_expenses
                else:
                    tbl2_height = number_payments

                new['number_order_details'] = new['number_order_details'] + number_order_details
                new['number_expenses'] = new['number_expenses'] + number_expenses
                new['number_payments'] = new['number_payments'] + number_payments

                new['rows'] = new['rows'] + tbl2_height

                largest = largest_among(new['number_order_details'], new['number_expenses'], new['number_payments'])

                order = {
                    'id': o.id,
                    'status': o.get_status_display(),
                    'client': o.client,
                    'total': o.total,
                    'create_at': o.create_at,
                    'order_detail': _order_detail,
                    'expenses': _expenses,
                    'payments': _payments,
                    'largest': largest,
                    'height': tbl2_height,
                    'number_order_details': number_order_details,
                    'number_expenses': number_expenses,
                    'number_payments': number_payments,
                    'distribution_mobil': distribution.id,
                    'type': o.type,
                }
                new.get('sales').append(order)
            _count_products = 0
            for key in product_dict:
                _vp = product_dict[key]['sold'] - product_dict[key]['borrowed']
                _recovered = product_dict[key]['i_void'] - _vp
                _owe = product_dict[key]['o_filled'] - (
                        product_dict[key]['sold'] + product_dict[key]['i_filled'] + product_dict[key]['i_ruined'])
                product = {
                    'pk': key,
                    'name': product_dict[key]['name'],
                    'sold': product_dict[key]['sold'],
                    'borrowed': product_dict[key]['borrowed'],
                    'recovered': _recovered,
                    'owe': _owe,
                }
                new.get('products').append(product)
                _count_products = _count_products + 1
            new['number_products'] = _count_products

            if (number_outputs >= number_inputs) and (number_outputs >= _count_products):
                tbl1_height = number_outputs
            elif (number_inputs >= number_outputs) and (number_inputs >= _count_products):
                tbl1_height = number_inputs
            else:
                tbl1_height = _count_products
            new['height'] = tbl1_height

            if new['rows'] < new['height']:
                new['rows'] = new['height']

    tpl = loader.get_template('comercial/distribution_queries_grid_list.html')
    context = ({
        'dictionary': dictionary,
        'sum_expenses': _sum_expenses,
        'sum_payments': _sum_payments,
        'dif_pe': _sum_payments - _sum_expenses,
        'is_pdf': is_pdf,
    })
    return tpl.render(context)


def largest_among(num1, num2, num3):
    largest = 0
    if (num1 >= num2) and (num1 >= num3):
        largest = num1
    elif (num2 >= num1) and (num2 >= num3):
        largest = num2
    else:
        largest = num3
    return largest


def get_distribution_mobil_recovered(request):
    if request.method == 'GET':
        pk = int(request.GET.get('pk', ''))

        distribution_mobil_obj = DistributionMobil.objects.get(id=pk)
        if distribution_mobil_obj.status == 'F':
            return JsonResponse({
                'error': 'LA PROGRAMACION YA ESTA FINALIZADA, POR FAVOR SELECCIONE OTRA',
            })
        # distribution_mobil_detail = DistributionDetail.objects.filter(distribution_mobil=distribution_mobil_obj)
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        # client_set = Client.objects.filter(order__distribution_mobil=distribution_mobil_obj.id,
        #                                  order__subsidiary_store__subsidiary=subsidiary_obj).distinct('id')
        # product_serialized_obj = serializers.serialize('json', product)
        client_set = Client.objects.filter(clientassociate__subsidiary=subsidiary_obj)
        t = loader.get_template('comercial/distribution_mobil_recovered.html')
        c = ({
            'distribution_mobil': distribution_mobil_obj,
            'client_set': client_set,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


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


def save_recovered_b(request):
    if request.method == 'GET':
        distribution_mobil_id = int(request.GET.get('distribution_mobil', ''))
        order_id = int(request.GET.get('order', ''))
        detail_order_id = int(request.GET.get('detail_order_id', ''))
        product = int(request.GET.get('product', ''))
        unit = int(request.GET.get('unit', ''))
        quantity_recover = request.GET.get('quantity_recover', '')
        distribution_mobil_obj = DistributionMobil.objects.get(id=distribution_mobil_id)
        order_obj = Order.objects.get(id=order_id)
        order_detail_obj = OrderDetail.objects.get(id=detail_order_id)
        product_obj = Product.objects.get(id=product)
        unit_obj = Unit.objects.get(id=unit)
        search_r_detail_distribution = DistributionDetail.objects.filter(distribution_mobil=distribution_mobil_obj,
                                                                         product=product_obj,
                                                                         status='R')

        if search_r_detail_distribution.count() > 0:
            item_with_qr = search_r_detail_distribution.last()
            item_with_qr.quantity = item_with_qr.quantity + decimal.Decimal(quantity_recover)
            item_with_qr.save()
        else:
            _r_new_detail_distribution = {
                'product': product_obj,
                'distribution_mobil': distribution_mobil_obj,
                'quantity': decimal.Decimal(quantity_recover),
                'unit': unit_obj,
                'status': 'R',
                'type': 'V',
            }
            _r_new_detail_distribution = DistributionDetail.objects.create(**_r_new_detail_distribution)
            _r_new_detail_distribution.save()

        loan_payment_obj = LoanPayment(
            price=order_detail_obj.price_unit,
            quantity=decimal.Decimal(quantity_recover),
            product=product_obj,
            order_detail=order_detail_obj,
            operation_date=datetime.now().date(),
            distribution_mobil=distribution_mobil_obj
        )
        loan_payment_obj.save()

        client_obj = order_obj.client
        order_set = Order.objects.filter(client=client_obj, type='R').order_by('id')
        return JsonResponse({
            'success': True,
            'message': 'Devolución realizada',
            'grid': get_dict_orders_details(order_set, client_obj),
        }, status=HTTPStatus.OK)


def get_advancement_client(request):
    if request.method == 'GET':
        pk = (request.GET.get('pk', ''))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        client_obj = Client.objects.filter(clientassociate__subsidiary=subsidiary_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        product_obj = Product.objects.filter(productstore__subsidiary_store__subsidiary=subsidiary_obj,
                                             productstore__subsidiary_store__category='I')
        if pk != '':
            distribution_mobil_obj = DistributionMobil.objects.get(id=int(pk))
            t = loader.get_template('comercial/client_advancement.html')
            c = ({
                'distribution_mobil': distribution_mobil_obj,
                'client_set': client_obj,
                'format': formatdate,
                'product_set': product_obj,
            })
            return JsonResponse({
                'form': t.render(c, request),
            })
        else:
            return render(request, 'comercial/subsidiary_advancement_client.html', {
                'client_set': client_obj,
                'format': formatdate,
                'product_set': product_obj,
            })


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
        if vehicle and driver:
            vehicle_obj = Truck.objects.get(id=int(vehicle))
            driver_obj = Driver.objects.get(id=int(driver))

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
        )
        guide_obj.save()

        for detail in data_guide['Details']:
            product_id = int(detail['Product'])
            product_obj = Product.objects.get(id=product_id)
            quantity = decimal.Decimal(detail['Quantity'])
            quantity_unit = decimal.Decimal(detail['QuantityUnit'])
            batch_id = int(detail['Batch'])
            batch_obj = Batch.objects.get(id=batch_id)
            unit_id = int(detail['Unit'])
            unit_obj = Unit.objects.get(id=unit_id)
            GuideDetail.objects.create(guide=guide_obj, product=product_obj,
                                       quantity=quantity_unit, unit=unit_obj, batch=batch_obj)
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
        product_store_set = ProductStore.objects.filter(subsidiary_store__id=subsidiary_store_id,
                                                        product__id=product_id)
        if product_store_set.exists():
            product_store_obj = product_store_set.last()
            last_batches = Batch.objects.filter(
                batch_number=OuterRef('batch_number'), product_store=product_store_obj).order_by('-id')

            latest_batches = Batch.objects.filter(
                product_store=product_store_obj
            ).annotate(last_id=Subquery(last_batches.values('id')[:1])).filter(id=F('last_id'), remaining_quantity__gt=0)

            if latest_batches.exists():
                product_obj = product_store_obj.product
                tpl = loader.get_template('comercial/modal_guide_batch.html')
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
            'modality_transport': g.get_modality_transport_display(),
            'carrier': g.carrier.name,
            'vehicle': g.vehicle.license_plate if g.vehicle else '-',
            'driver': g.driver.names if g.driver else '-',
            'weight': str(round(g.weight, 2)),
            'package': str(round(g.package)),
            'date_issue': g.date_issue,
            'transfer_date': g.transfer_date,
            'contract_detail': g.contract_detail,
            'guide_motive': g.guide_motive.description,
            'observation': g.observation,
            'count': g.guidedetail_set.count(),
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


def modal_picking_create(request):
    from collections import defaultdict
    if request.method == 'GET':
        guides_ids = sorted(json.loads(request.GET.get('guides', '[]')))
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        formattime = my_date.strftime("%H:%M:%S")
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        unit_description = ''
        guide_numbers = []
        all_purchases_ids = []
        purchase_dict = []
        acc_total = 0
        quantity_total = 0

        supplier_name = ''
        supplier_address = ''
        grouped_by_product = {}

        if guides_ids:
            guide_details = GuideDetail.objects.filter(
                guide_id__in=guides_ids
            ).select_related('product', 'unit', 'batch')

            for detail in guide_details:
                product = detail.product
                product_id = product.id
                quantity = float(detail.quantity)
                weight_kg = product.weight / 1000
                weight = quantity * float(weight_kg)

                if product_id not in grouped_by_product:

                    grouped_by_product[product_id] = {
                        'product_code': product.code,
                        'product_name': product.name,
                        'details': [],
                        'total_quantity': 0.0,
                        'total_weight': 0.0,
                    }

                grouped_by_product[product_id]['details'].append({
                    'quantity': str(round(detail.quantity)),
                    'unit': detail.unit.name,
                    'batch': detail.batch.batch_number if detail.batch else None,
                    'weight': str(round(detail.quantity * weight_kg))
                })

                grouped_by_product[product_id]['total_quantity'] += quantity
                grouped_by_product[product_id]['total_weight'] += weight

                for p_data in grouped_by_product.values():
                    p_data['total_quantity'] = round(p_data['total_quantity'], 0)
                    p_data['total_weight'] = round(p_data['total_weight'], 0)
            # for p in guides_ids:
            #     guide_obj = Guide.objects.get(id=p)
            #     guide_details = GuideDetail.objects.filter(guide=guide_obj)
            #     serial_number = f'{guide_obj.serial} {guide_obj.correlative}'
            #     guide_numbers.append(serial_number)
            #     all_purchases_ids.append(p)
            #
            #     item_purchase = {
            #         'purchases': all_purchases_ids,
            #         'oc_number': guide_numbers,
            #         'details': []
            #     }
            #
            #     for pd in guide_details:
            #         product_id = pd.product.id
            #         unit_id = pd.unit.id
            #         quantity_total_invoice = 0
            #         product_detail = ProductDetail.objects.filter(product_id=product_id, unit_id=unit_id).last()
            #         quantity = pd.quantity - quantity_total_invoice
            #
            #         item_detail = {
            #             'detail_id': pd.id,
            #             'product_id': product_id,
            #             'product_name': pd.product.name,
            #             'unit_id': unit_id,
            #             'unit_name': pd.unit.name,
            #             'unit_description': pd.unit.description,
            #             'quantity': quantity,
            #             'quantity_minimum': product_detail.quantity_minimum,
            #         }
            #         quantity_total += quantity
            #         item_purchase.get('details').append(item_detail)
            #     purchase_dict.append(item_purchase)
            #
            # base_total = acc_total / decimal.Decimal(1.18)
            # igv_total = acc_total - base_total
            t = loader.get_template('comercial/modal_picking_create.html')
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
                'details_product': grouped_by_product,
                'quantity_total': round(quantity_total, 0),
                # 'base_total': round(base_total, 2),
                # 'igv_total': round(igv_total, 2),
                # 'bill_total': round(acc_total, 2),
                # 'first_address': first_address,
            })
            return JsonResponse({
                'form': t.render(c, request),
            })