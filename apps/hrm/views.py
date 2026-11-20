from django.db import DatabaseError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View, CreateView, UpdateView, FormView
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from http import HTTPStatus
from .models import *
from apps.sales.models import *
from apps.comercial.models import *
from apps.accounting.models import *
from .forms import *
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import ImageFieldFile
from django.template import loader
from datetime import datetime
from django.contrib.auth.hashers import make_password
from django.db.models import Min, Sum, Max, Q, Count, F, Prefetch
from django.db.models.functions import Coalesce
# This is the default low-level cache.
from django.views.decorators.cache import cache_page
from django.core.cache import cache


class Home(TemplateView):
    """Dashboard principal del ERP con indicadores del proceso comercial."""

    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        from decimal import Decimal
        from django.db.models import DecimalField, Value
        from django.db.models.functions import TruncMonth
        from django.utils import timezone
        from apps.buys.models import Purchase, PurchaseDetail
        from apps.sales.models import Requirement

        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        current_subsidiary = None
        try:
            current_subsidiary = get_subsidiary_by_user(self.request.user)
        except Exception:
            current_subsidiary = None

        order_qs = Order.objects.filter(order_type='V').exclude(status='A')
        if current_subsidiary:
            order_qs = order_qs.filter(subsidiary=current_subsidiary)

        purchase_qs = Purchase.objects.filter(status__in=['S', 'A'])
        if current_subsidiary:
            purchase_qs = purchase_qs.filter(subsidiary=current_subsidiary)

        month_sales = order_qs.filter(
            create_at__year=today.year, create_at__month=today.month
        ).aggregate(total=Coalesce(Sum('total'), Value(0), output_field=DecimalField(max_digits=14, decimal_places=2)))['total'] or Decimal('0')
        total_sales = order_qs.aggregate(
            total=Coalesce(Sum('total'), Value(0), output_field=DecimalField(max_digits=14, decimal_places=2))
        )['total'] or Decimal('0')
        month_orders = order_qs.filter(create_at__year=today.year, create_at__month=today.month).count()
        month_quotes = Order.objects.filter(
            order_type='T', create_at__year=today.year, create_at__month=today.month
        ).count()

        totals = order_qs.aggregate(
            total=Coalesce(Sum('total'), Value(0), output_field=DecimalField(max_digits=14, decimal_places=2)),
            paid=Coalesce(Sum('total_payed'), Value(0), output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
        receivable = (totals['total'] or Decimal('0')) - (totals['paid'] or Decimal('0'))

        purchases_total = PurchaseDetail.objects.filter(
            purchase__in=purchase_qs
        ).aggregate(
            total=Coalesce(
                Sum(F('quantity') * F('price_unit')),
                Value(0),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            )
        )['total'] or Decimal('0')

        low_stock_qs = ProductStore.objects.filter(stock__lte=5).select_related(
            'product', 'subsidiary_store__subsidiary'
        )
        if current_subsidiary:
            low_stock_qs = low_stock_qs.filter(subsidiary_store__subsidiary=current_subsidiary)

        requirements_qs = Requirement.objects.exclude(status__in=['3', '6'])
        if current_subsidiary:
            requirements_qs = requirements_qs.filter(subsidiary=current_subsidiary)

        # Ventas de los últimos seis meses para el gráfico del dashboard.
        chart_qs = order_qs.filter(create_at__isnull=False).annotate(month=TruncMonth('create_at')).values('month').annotate(
            total=Sum('total')
        ).order_by('month')
        chart_map = {item['month'].strftime('%Y-%m'): float(item['total'] or 0) for item in chart_qs if item['month']}
        chart_labels, chart_values = [], []
        year, month = today.year, today.month
        for offset in range(5, -1, -1):
            m = month - offset
            y = year
            while m <= 0:
                m += 12
                y -= 1
            key = f'{y:04d}-{m:02d}'
            chart_labels.append(['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'][m - 1])
            chart_values.append(chart_map.get(key, 0))
        chart_max = max(chart_values) if chart_values else 0
        chart_bars = [
            {'label': label, 'value': value, 'height': (value / chart_max * 100) if chart_max else 0}
            for label, value in zip(chart_labels, chart_values)
        ]

        context.update({
            'subsidiary_set': Subsidiary.objects.filter(is_address=False).order_by('id', 'serial'),
            'current_subsidiary': current_subsidiary,
            'today': today,
            'month_sales': month_sales,
            'total_sales': total_sales,
            'month_orders': month_orders,
            'month_quotes': month_quotes,
            'receivable': receivable,
            'purchases_total': purchases_total,
            'pending_purchases': purchase_qs.filter(status='S').count(),
            'warehouse_purchases': purchase_qs.filter(status='A').count(),
            'low_stock': low_stock_qs.order_by('stock')[:6],
            'low_stock_count': low_stock_qs.count(),
            'requirements_pending': requirements_qs.count(),
            'recent_orders': order_qs.select_related('client').order_by('-id')[:7],
            'recent_purchases': purchase_qs.select_related('supplier').order_by('-id')[:7],
            'chart_bars': chart_bars,
        })
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


def get_sales_vs_expenses(subsidiary_obj=None, start_date=None, end_date=None):
    """Compara ventas y gastos por canal de venta.

    La implementación anterior agrupaba por ``distribution_mobil``, un modelo
    que fue retirado del proyecto junto con el módulo de reparto incompleto.
    Se conserva la estructura de salida (``i_sales``, ``i_expenses``, ``pk``,
    ``name``) pero agrupando por el campo vigente ``Order.sale_type``.
    """
    result = {}
    for key, label in Order.SALE_TYPE_CHOICES:
        result[key] = {
            'i_sales': '0.0',
            'i_expenses': '0.0',
            'pk': key,
            'name': label,
        }

    orders = Order.objects.filter(order_type='V')
    if start_date and end_date:
        orders = orders.filter(create_at__date__range=(start_date, end_date))
    if subsidiary_obj is not None:
        orders = orders.filter(subsidiary=subsidiary_obj)
    for row in orders.values('sale_type').annotate(total=Sum('total')):
        key = row['sale_type']
        if key in result and row['total']:
            result[key]['i_sales'] = str(float(round(row['total'], 2)))

    expenses = CashFlow.objects.filter(type='S', order__isnull=False)
    if start_date and end_date:
        expenses = expenses.filter(transaction_date__date__range=(start_date, end_date))
    if subsidiary_obj is not None:
        expenses = expenses.filter(order__subsidiary=subsidiary_obj)
    for row in expenses.values('order__sale_type').annotate(total=Sum('total')):
        key = row['order__sale_type']
        if key in result and row['total']:
            result[key]['i_expenses'] = str(float(round(row['total'], 2)))

    return result


# FUNCION PARA RECUPERAR EL USUARIO DE UNA SUCURSAL


def get_subsidiary_by_user_id(user_id):

    user_obj = User.objects.prefetch_related(
        Prefetch('worker_set__establishment_set__subsidiary'),
    ).get(id=user_id)

    worker_obj = user_obj.worker_set.all().last()
    establishment_obj = worker_obj.establishment_set.all().last()
    subsidiary_obj = establishment_obj.subsidiary
    return subsidiary_obj


def get_subsidiary_by_user(user_obj):
    # cache_key = 'subsidiary'
    # cache_time = 7200
    # data = cache.get(cache_key)
    # if not data:
    worker_obj = Worker.objects.get(user=user_obj)
    establishment_obj = Establishment.objects.filter(worker=worker_obj).last()
    subsidiary = Subsidiary.objects.filter(establishment=establishment_obj).first()
    # cache.set(cache_key, subsidiary, cache_time)
    return subsidiary


def get_employee_queryset():
    """Queryset optimizado para lista de empleados (prefetch/select_related)."""
    return Employee.objects.all().select_related(
        'document_type', 'document_issuing_country'
    ).prefetch_related(
        Prefetch(
            'worker_set',
            queryset=Worker.objects.select_related(
                'occupation_private_sector', 'occupation_public_sector', 'user'
            ).prefetch_related(
                Prefetch(
                    'establishment_set',
                    queryset=Establishment.objects.select_related('subsidiary').order_by('-id')
                )
            ).order_by('-id')
        )
    ).order_by('-created_at')


# Create your views here.
class EmployeeList(View):
    model = Employee
    form_class = FormEmployee
    template_name = 'hrm/employee_list.html'

    def get_queryset(self):
        return get_employee_queryset()

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['employees'] = self.get_queryset()
        contexto['form'] = self.form_class
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class JsonEmployeeList(View):
    def get(self, request):
        employees = get_employee_queryset()
        t = loader.get_template('hrm/employee_grid_list.html')
        c = {'employees': employees}
        return JsonResponse({'result': t.render(c, request)})


class ProfileView(View):
    """Perfil del empleado con enlaces a modelos relacionados."""
    template_name = 'hrm/profile.html'

    def get(self, request, *args, **kwargs):
        worker = None
        employee = None
        try:
            worker = Worker.objects.select_related(
                'employee', 'occupation_private_sector', 'occupation_public_sector', 'user'
            ).prefetch_related(
                Prefetch('establishment_set', queryset=Establishment.objects.select_related('subsidiary').order_by('-id'))
            ).filter(user=request.user).order_by('-id').first()
            if worker:
                employee = worker.employee
        except Exception:
            pass
        return render(request, self.template_name, {
            'employee': employee,
            'worker': worker,
            'user': request.user,
        })


class PasswordChangeView(FormView):
    """Vista para cambio de contraseña del usuario."""
    template_name = 'hrm/settings_password.html'
    form_class = PasswordChangeForm

    def get_success_url(self):
        return reverse('hrm:password_change_done')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        update_session_auth_hash(self.request, form.user)
        return redirect('hrm:password_change_done')


class PasswordChangeDoneView(TemplateView):
    template_name = 'hrm/settings_password_done.html'


class JsonEmployeeCreate(CreateView):
    model = Employee
    form_class = FormEmployee
    template_name = 'hrm/employee_create.html'

    def post(self, request):
        # Recibe como parámetro una representación de un diccionario
        data = dict()
        # if not request.POST._mutable:
        #     request.POST._mutable = True
        # if request.POST['address_1_road_type'] == '0':
        #     request.POST['address_1_road_type'] = ''
        form = FormEmployee(request.POST, request.FILES)

        if form.is_valid():
            print('isvalid()')
            employee = form.save()
            # converting a database model to a dictionary...
            data['employee'] = model_to_dict(employee)
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


class JsonEmployeeUpdate(UpdateView):
    model = Employee
    form_class = FormEmployee
    template_name = 'hrm/employee_update.html'

    def post(self, request, pk):
        data = dict()
        employee = self.model.objects.get(pk=pk)
        # form = SnapForm(request.POST, request.FILES, instance=instance)
        form = self.form_class(instance=employee, data=request.POST, files=request.FILES)
        if form.is_valid():
            employee = form.save()
            data['employee'] = model_to_dict(employee)
            result = json.dumps(data, cls=ExtendedEncoder)
            response = JsonResponse(result, safe=False)
            response.status_code = HTTPStatus.OK
        else:
            data['error'] = "form not valid!"
            data['form_invalid'] = form.errors
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


class ExtendedEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, ImageFieldFile):
            return str(o)
        else:
            return super().default(o)


def get_worker_designation(request):
    if request.method == 'GET':
        data = dict()
        pk = request.GET.get('pk', '')
        try:
            employee_obj = Employee.objects.get(id=pk)
        except Employee.DoesNotExist:
            data['error'] = "empleado no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        # Worker_obj = Worker.objects.get(employee=employee_obj)
        form_obj = FormWorker()
        form_period_obj = FormPeriod()
        form_establishment_obj = FormEstablishment()
        form_payment_account_data_obj = FormPaymentAccountData()
        current_date = datetime.now()
        worker_types = WorkerType.objects.all()
        pensioner_regimes = PensionerRegime.objects.all()
        labor_regimes = LaborRegime.objects.all()
        occupational_categories = OccupationalCategory.objects.all()
        formatdate = current_date.strftime("%Y-%m-%d")
        print(formatdate)
        t = loader.get_template('hrm/employee_worker_designation.html')
        c = ({
            'employee': employee_obj,
            'form': form_obj,
            'form_period': form_period_obj,
            'formatdate': formatdate,
            'form_establishment': form_establishment_obj,
            'form_payment_account_data': form_payment_account_data_obj,
            'worker_types': worker_types,
            'pensioner_regimes': pensioner_regimes,
            'labor_regimes': labor_regimes,
            'occupational_categories': occupational_categories,
        })

        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def create_worker(request):
    if request.method == 'POST':

        employee = request.POST.get('employee')
        employee_obj = Employee.objects.get(id=int(employee))

        period_start_date = request.POST.get('period_start_date')
        period_end_date = request.POST.get('period_end_date')
        reason_for_withdrawal = request.POST.get('reason_for_withdrawal')

        worker_type = request.POST.get('worker_type')
        worker_type_obj = WorkerType.objects.get(id=worker_type)

        worker_type_start_date = request.POST.get('worker_type_start_date')
        worker_type_end_date = request.POST.get('worker_type_end_date')

        labor_regime = request.POST.get('labor_regime')
        labor_regime_obj = LaborRegime.objects.get(id=labor_regime)
        occupational_category = request.POST.get('occupational_category')
        occupational_category_obj = OccupationalCategory.objects.get(id=occupational_category)

        occupation_private_sector = request.POST.get('occupation_private_sector')
        occupation_public_sector = request.POST.get('occupation_public_sector')
        occupation_public_sector_obj = None
        occupation_private_sector_obj = None
        if labor_regime == '01':
            if occupation_private_sector != '':
                occupation_private_sector_obj = OccupationPrivateSector.objects.get(id=occupation_private_sector)
            else:
                response = JsonResponse({'error': "Elija ocupacion del sector privado."})
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        else:
            if labor_regime == '02':

                if occupation_public_sector != '':
                    occupation_public_sector_obj = OccupationPublicSector.objects.get(id=occupation_public_sector)
                else:
                    response = JsonResponse({'error': "Elija ocupacion del sector publico."})
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

        contract_type = request.POST.get('contract_type')
        if contract_type != '':
            contract_type_obj = ContractType.objects.get(id=contract_type)
        else:
            response = JsonResponse({'error': "Elija tipo de contrato."})
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        payment_type = request.POST.get('payment_type')
        periodicity = request.POST.get('periodicity')

        initial_basic_remuneration = request.POST.get('initial_basic_remuneration')

        subject_to_maximum_working_day = 0
        if request.POST.get('subject_to_maximum_working_day') is not None:
            subject_to_maximum_working_day = 1

        subject_to_atypical_regime = 0
        if request.POST.get('subject_to_atypical_regime') is not None:
            subject_to_atypical_regime = 1

        subject_to_night_time = 0
        if request.POST.get('subject_to_night_time') is not None:
            subject_to_night_time = 1

        special_situation = request.POST.get('special_situation')
        special_situation_obj = SpecialSituation.objects.get(id=special_situation)

        disability = 0
        if request.POST.get('disability') is not None:
            disability = 1

        is_unionized = 0
        if request.POST.get('is_unionized') is not None:
            is_unionized = 1

        situation = request.POST.get('situation')

        situation_obj = Situation.objects.get(id=situation)

        health_insurance_regime = request.POST.get('health_insurance_regime')
        health_insurance_regime_obj = HealthInsuranceRegime.objects.get(id=health_insurance_regime)
        health_insurance_regime_start_date = request.POST.get('health_insurance_regime_start_date')
        health_insurance_regime_end_date = request.POST.get('health_insurance_regime_end_date')

        pensioner_regime = request.POST.get('pensioner_regime')
        pensioner_regime_obj = PensionerRegime.objects.get(id=pensioner_regime)
        cuspp = request.POST.get('cuspp')
        pensioner_regime_start_date = request.POST.get('pensioner_regime_start_date')
        pensioner_regime_end_date = request.POST.get('pensioner_regime_end_date')

        sctr_pension = request.POST.get('sctr_pension', '0')
        sctr_health_start_date = request.POST.get('sctr_health_start_date')
        sctr_health_end_date = request.POST.get('sctr_health_end_date')

        educational_situation = request.POST.get('educational_situation')
        educational_situation_obj = EducationalSituation.objects.get(id=educational_situation)

        exempted_5th_category_rent = 0
        if request.POST.get('exempted_5th_category_rent') is not None:
            exempted_5th_category_rent = 1

        agreement_to_avoid_double_taxation = 0
        if request.POST.get('agreement_to_avoid_double_taxation') is not None:
            agreement_to_avoid_double_taxation = 1

        subsidiary = request.POST.get('subsidiary')
        subsidiary_obj = Subsidiary.objects.get(id=subsidiary)

        financial_system_entity = request.POST.get('financial_system_entity')
        account_number_where_the_remuneration_is_paid = request.POST.get(
            'account_number_where_the_remuneration_is_paid')

        user = request.POST.get('user', '')
        create_user = 0
        if request.POST.get('create_user') is not None:
            create_user = 1

        user_obj = None
        if user != '':
            user_obj = User.objects.get(id=user)
            if user_obj.employee is not None:
                response = JsonResponse({'error': "Este usuario ya esta siendo utilizado por otro empleado."})
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
        else:
            if bool(create_user):
                username = employee_obj.names.lower()[:1] + employee_obj.paternal_last_name.lower() + str(
                    employee_obj.id)
                user_email = username + '@user.com'
                user_obj = User(
                    username=username,
                    email=user_email,
                )
                user_obj.set_password(employee_obj.document_number)
                user_obj.save()

        worker_obj = Worker(
            employee=employee_obj,  # oblig
            labor_regime=labor_regime_obj,  # oblig
            educational_situation=educational_situation_obj,  # oblig
            occupation_public_sector=occupation_public_sector_obj,  #
            occupation_private_sector=occupation_private_sector_obj,  # oblig
            disability=bool(int(disability)),  # oblig
            cuspp=cuspp,  #
            sctr_pension=sctr_pension,  #
            contract_type=contract_type_obj,  # oblig
            subject_to_atypical_regime=bool(int(subject_to_atypical_regime)),  # oblig
            subject_to_maximum_working_day=bool(int(subject_to_maximum_working_day)),  # oblig
            subject_to_night_time=bool(int(subject_to_night_time)),  # oblig
            is_unionized=bool(int(is_unionized)),  # oblig
            periodicity=periodicity,  # oblig
            initial_basic_remuneration=float(initial_basic_remuneration),  # oblig
            situation=situation_obj,  # oblig
            exempted_5th_category_rent=bool(int(exempted_5th_category_rent)),  # oblig
            special_situation=special_situation_obj,  # oblig
            payment_type=payment_type,  # oblig
            occupational_category=occupational_category_obj,  #
            agreement_to_avoid_double_taxation=agreement_to_avoid_double_taxation,  # oblig
            user=user_obj
        )
        # print(worker_obj)
        worker_obj.save()

        period_obj1 = Period(
            worker=worker_obj,
            category='1',  # Trabajador
            register_type='1',  # Período
            start_or_restart_date=period_start_date,
        )
        period_obj1.save()

        period_obj2 = Period(
            worker=worker_obj,
            category='1',  # Trabajador
            register_type='2',  # Tipo de trabajador
            start_or_restart_date=worker_type_start_date,
            indicator_of_the_type_of_registration=str(worker_type_obj.id),
            worker_type=worker_type_obj
        )
        period_obj2.save()

        period_obj3 = Period(
            worker=worker_obj,
            category='1',  # Trabajador
            register_type='3',  # Régimen de Aseguramiento de Salud
            start_or_restart_date=health_insurance_regime_start_date,
            indicator_of_the_type_of_registration=str(health_insurance_regime_obj.id),
            health_insurance_regime=health_insurance_regime_obj
        )
        period_obj3.save()

        period_obj4 = Period(
            worker=worker_obj,
            category='1',  # Trabajador
            register_type='4',  # Régimen pensionario
            start_or_restart_date=pensioner_regime_start_date,
            indicator_of_the_type_of_registration=str(pensioner_regime_obj.id),
            pensioner_regime=pensioner_regime_obj
        )
        period_obj4.save()

        establishment_obj = Establishment(
            worker=worker_obj,
            subsidiary=subsidiary_obj,
            ruc_own=subsidiary_obj.ruc,
        )
        establishment_obj.save()

        if financial_system_entity != '':
            financial_system_entity_obj = FinancialSystemEntity.objects.get(id=financial_system_entity)
            payment_account_data_obj = PaymentAccountData(
                worker=worker_obj,
                financial_system_entity=financial_system_entity_obj,
                account_number_where_the_remuneration_is_paid=account_number_where_the_remuneration_is_paid,
            )
            payment_account_data_obj.save()

        return JsonResponse({
            'success': True,
            # 'form': t.render(c),
        }, status=HTTPStatus.OK)


def get_establishment_code(request):
    if request.method == 'GET':
        id_subsidiary = request.GET.get('subsidiary', '')
        subsidiary_obj = Subsidiary.objects.get(id=int(id_subsidiary))
        return JsonResponse({
            'serial': subsidiary_obj.serial,
            'address': subsidiary_obj.address,
            'message': 'Codigo de sede recuperado.',
        }, status=HTTPStatus.OK)


def get_worker_establishment(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        worker_obj = Worker.objects.prefetch_related(
            Prefetch('establishment_set', queryset=Establishment.objects.select_related('subsidiary').order_by('-id'))
        ).get(id=pk)
        form_establishment_obj = FormEstablishment()
        t = loader.get_template('hrm/worker_establishment.html')
        c = ({
            'worker': worker_obj,
            'form': form_establishment_obj,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def update_worker_establishment(request):
    if request.method == 'POST':
        worker = request.POST.get('worker')
        subsidiary = request.POST.get('subsidiary')
        if not worker or not subsidiary:
            return JsonResponse({'error': 'Datos incompletos'}, status=HTTPStatus.BAD_REQUEST)
        try:
            worker_obj = Worker.objects.get(id=int(worker), user=request.user)
            subsidiary_obj = Subsidiary.objects.get(id=int(subsidiary))
        except (Worker.DoesNotExist, Subsidiary.DoesNotExist, ValueError):
            return JsonResponse({'error': 'Trabajador o sucursal no válidos'}, status=HTTPStatus.BAD_REQUEST)

        establishment_obj = Establishment.objects.filter(worker=worker_obj).last()
        if not establishment_obj:
            establishment_obj = Establishment(
                worker=worker_obj,
                subsidiary=subsidiary_obj,
                ruc_own=subsidiary_obj.ruc,
            )
            establishment_obj.save()
        else:
            establishment_obj.subsidiary = subsidiary_obj
            establishment_obj.ruc_own = subsidiary_obj.ruc
            establishment_obj.save()

        return JsonResponse({'success': True}, status=HTTPStatus.OK)
    return JsonResponse({'error': 'Petición incorrecta'}, status=HTTPStatus.BAD_REQUEST)


def get_worker_user(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        worker_obj = Worker.objects.get(id=pk)
        t = loader.get_template('hrm/worker_user.html')
        c = ({
            'worker': worker_obj,
        })
        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def update_worker_user(request):
    if request.method == 'POST':

        worker = request.POST.get('worker')
        worker_obj = Worker.objects.get(id=int(worker))

        username = request.POST.get('username')
        password = request.POST.get('key')
        is_staff = False
        if request.POST.get('is_staff') is not None:
            is_staff = bool(request.POST.get('is_staff'))

        try:
            user_obj = User.objects.get(worker=worker_obj)
        except User.DoesNotExist:
            user_obj = None

        if user_obj is not None:
            if len(username) > 0:
                if user_obj.username != username:
                    user_obj.username = username
            if len(password) >= 6:
                user_obj.set_password(password)
        else:
            user_email = username + '@user.com'
            user_obj = User(
                username=username,
                email=user_email,
            )
            user_obj.set_password(password)
        user_obj.is_staff = is_staff
        try:
            user_obj.save()
        except DatabaseError as e:
            data = {'error': str(e)}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        worker_obj.user = user_obj
        worker_obj.save()
        return JsonResponse({
            'success': True,
            # 'form': t.render(c),
        }, status=HTTPStatus.OK)
    data = {'error': 'Peticion incorrecta'}
    response = JsonResponse(data)
    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    return response


def edit_worker_designation(request):
    if request.method == 'GET':
        data = dict()
        pk = request.GET.get('pk', '')
        try:
            worker_obj = Worker.objects.get(id=pk)
        except Worker.DoesNotExist:
            data['error'] = "empleado no existe!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
        # Período
        period_obj1 = Period.objects.filter(worker=worker_obj, category='1', register_type='1').last()
        # Tipo de trabajador
        period_obj2 = Period.objects.filter(worker=worker_obj, category='1', register_type='2').last()
        # Régimen de Aseguramiento de Salud
        period_obj3 = Period.objects.filter(worker=worker_obj, category='1', register_type='3').last()
        # Régimen pensionario
        period_obj4 = Period.objects.filter(worker=worker_obj, category='1', register_type='4').last()

        establishment_obj = Establishment.objects.filter(worker=worker_obj).last()
        payment_account_data_obj = PaymentAccountData.objects.filter(worker=worker_obj).last()

        form_obj = FormWorker()
        form_period_obj = FormPeriod()
        form_establishment_obj = FormEstablishment()
        form_payment_account_data_obj = FormPaymentAccountData()
        current_date = datetime.now()
        worker_types = WorkerType.objects.all()
        pensioner_regimes = PensionerRegime.objects.all()
        labor_regimes = LaborRegime.objects.all()
        occupational_categories = OccupationalCategory.objects.all()
        formatdate = current_date.strftime("%Y-%m-%d")

        t = loader.get_template('hrm/employee_worker_update_designation.html')
        c = ({
            'worker': worker_obj,
            'period1': period_obj1,
            'period2': period_obj2,
            'period3': period_obj3,
            'period4': period_obj4,
            'establishment': establishment_obj,
            'payment_account': payment_account_data_obj,
            'form': form_obj,
            'form_period': form_period_obj,
            'formatdate': formatdate,
            'form_establishment': form_establishment_obj,
            'form_payment_account_data': form_payment_account_data_obj,
            'worker_types': worker_types,
            'pensioner_regimes': pensioner_regimes,
            'labor_regimes': labor_regimes,
            'occupational_categories': occupational_categories,
        })

        return JsonResponse({
            'success': True,
            'form': t.render(c, request),
        })


def update_worker(request):
    if request.method == 'POST':

        worker = request.POST.get('worker')
        worker_obj = Worker.objects.get(id=int(worker))

        period_start_date = request.POST.get('period_start_date')
        period_end_date = request.POST.get('period_end_date')
        reason_for_withdrawal = request.POST.get('reason_for_withdrawal')

        worker_type = request.POST.get('worker_type')
        worker_type_obj = WorkerType.objects.get(id=worker_type)

        worker_type_start_date = request.POST.get('worker_type_start_date')
        worker_type_end_date = request.POST.get('worker_type_end_date')

        labor_regime = request.POST.get('labor_regime')
        labor_regime_obj = LaborRegime.objects.get(id=labor_regime)
        occupational_category = request.POST.get('occupational_category')
        occupational_category_obj = OccupationalCategory.objects.get(id=occupational_category)

        occupation_private_sector = request.POST.get('occupation_private_sector')
        occupation_public_sector = request.POST.get('occupation_public_sector')
        occupation_public_sector_obj = None
        occupation_private_sector_obj = None
        if labor_regime == '01':
            if occupation_private_sector != '':
                occupation_private_sector_obj = OccupationPrivateSector.objects.get(id=occupation_private_sector)
            else:
                response = JsonResponse({'error': "Elija ocupacion del sector privado."})
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        else:
            if labor_regime == '02':

                if occupation_public_sector != '':
                    occupation_public_sector_obj = OccupationPublicSector.objects.get(id=occupation_public_sector)
                else:
                    response = JsonResponse({'error': "Elija ocupacion del sector publico."})
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response

        contract_type = request.POST.get('contract_type')
        if contract_type != '':
            contract_type_obj = ContractType.objects.get(id=contract_type)
        else:
            response = JsonResponse({'error': "Elija tipo de contrato."})
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        payment_type = request.POST.get('payment_type')
        periodicity = request.POST.get('periodicity')

        initial_basic_remuneration = request.POST.get('initial_basic_remuneration')

        subject_to_maximum_working_day = 0
        if request.POST.get('subject_to_maximum_working_day') is not None:
            subject_to_maximum_working_day = 1

        subject_to_atypical_regime = 0
        if request.POST.get('subject_to_atypical_regime') is not None:
            subject_to_atypical_regime = 1

        subject_to_night_time = 0
        if request.POST.get('subject_to_night_time') is not None:
            subject_to_night_time = 1

        special_situation = request.POST.get('special_situation')
        special_situation_obj = SpecialSituation.objects.get(id=special_situation)

        disability = 0
        if request.POST.get('disability') is not None:
            disability = 1

        is_unionized = 0
        if request.POST.get('is_unionized') is not None:
            is_unionized = 1

        situation = request.POST.get('situation')

        situation_obj = Situation.objects.get(id=situation)

        health_insurance_regime = request.POST.get('health_insurance_regime')
        health_insurance_regime_obj = HealthInsuranceRegime.objects.get(id=health_insurance_regime)
        health_insurance_regime_start_date = request.POST.get('health_insurance_regime_start_date')
        health_insurance_regime_end_date = request.POST.get('health_insurance_regime_end_date')

        pensioner_regime = request.POST.get('pensioner_regime')
        pensioner_regime_obj = PensionerRegime.objects.get(id=pensioner_regime)
        cuspp = request.POST.get('cuspp')
        pensioner_regime_start_date = request.POST.get('pensioner_regime_start_date')
        pensioner_regime_end_date = request.POST.get('pensioner_regime_end_date')

        sctr_pension = request.POST.get('sctr_pension', '0')
        sctr_health_start_date = request.POST.get('sctr_health_start_date')
        sctr_health_end_date = request.POST.get('sctr_health_end_date')

        educational_situation = request.POST.get('educational_situation')
        educational_situation_obj = EducationalSituation.objects.get(id=educational_situation)

        exempted_5th_category_rent = 0
        if request.POST.get('exempted_5th_category_rent') is not None:
            exempted_5th_category_rent = 1

        agreement_to_avoid_double_taxation = 0
        if request.POST.get('agreement_to_avoid_double_taxation') is not None:
            agreement_to_avoid_double_taxation = 1

        subsidiary = request.POST.get('subsidiary')
        subsidiary_obj = Subsidiary.objects.get(id=subsidiary)

        financial_system_entity = request.POST.get('financial_system_entity')
        account_number_where_the_remuneration_is_paid = request.POST.get(
            'account_number_where_the_remuneration_is_paid')

        worker_obj.labor_regime = labor_regime_obj  # oblig
        worker_obj.educational_situation = educational_situation_obj  # oblig
        worker_obj.occupation_public_sector = occupation_public_sector_obj  #
        worker_obj.occupation_private_sector = occupation_private_sector_obj  # oblig
        worker_obj.disability = bool(int(disability))  # oblig
        worker_obj.cuspp = cuspp  #
        worker_obj.sctr_pension = sctr_pension  #
        worker_obj.contract_type = contract_type_obj  # oblig
        worker_obj.subject_to_atypical_regime = bool(int(subject_to_atypical_regime))  # oblig
        worker_obj.subject_to_maximum_working_day = bool(int(subject_to_maximum_working_day))  # oblig
        worker_obj.subject_to_night_time = bool(int(subject_to_night_time))  # oblig
        worker_obj.is_unionized = bool(int(is_unionized))  # oblig
        worker_obj.periodicity = periodicity  # oblig
        worker_obj.initial_basic_remuneration = float(initial_basic_remuneration)  # oblig
        worker_obj.situation = situation_obj  # oblig
        worker_obj.exempted_5th_category_rent = bool(int(exempted_5th_category_rent))  # oblig
        worker_obj.special_situation = special_situation_obj  # oblig
        worker_obj.payment_type = payment_type  # oblig
        worker_obj.occupational_category = occupational_category_obj  #
        worker_obj.agreement_to_avoid_double_taxation = agreement_to_avoid_double_taxation  # oblig
        worker_obj.save()

        # Período
        period_obj1 = Period.objects.filter(worker=worker_obj, category='1', register_type='1').last()
        # Tipo de trabajador
        period_obj2 = Period.objects.filter(worker=worker_obj, category='1', register_type='2').last()
        # Régimen de Aseguramiento de Salud
        period_obj3 = Period.objects.filter(worker=worker_obj, category='1', register_type='3').last()
        # Régimen pensionario
        period_obj4 = Period.objects.filter(worker=worker_obj, category='1', register_type='4').last()

        establishment_obj = Establishment.objects.filter(worker=worker_obj).last()
        payment_account_data_obj = PaymentAccountData.objects.filter(worker=worker_obj).last()

        period_obj1.start_or_restart_date = period_start_date
        period_obj1.save()

        period_obj2.start_or_restart_date = worker_type_start_date
        period_obj2.indicator_of_the_type_of_registration = str(worker_type_obj.id)
        period_obj2.worker_type = worker_type_obj
        period_obj2.save()

        period_obj3.start_or_restart_date = health_insurance_regime_start_date
        period_obj3.indicator_of_the_type_of_registration = str(health_insurance_regime_obj.id)
        period_obj3.health_insurance_regime = health_insurance_regime_obj
        period_obj3.save()

        period_obj4.start_or_restart_date = pensioner_regime_start_date
        period_obj4.indicator_of_the_type_of_registration = str(pensioner_regime_obj.id)
        period_obj4.pensioner_regime = pensioner_regime_obj
        period_obj4.save()

        establishment_obj.subsidiary = subsidiary_obj
        establishment_obj.ruc_own = subsidiary_obj.ruc
        establishment_obj.save()

        if financial_system_entity != '':
            financial_system_entity_obj = FinancialSystemEntity.objects.get(id=financial_system_entity)
            if payment_account_data_obj:
                payment_account_data_obj.financial_system_entity = financial_system_entity_obj
                payment_account_data_obj.account_number_where_the_remuneration_is_paid = account_number_where_the_remuneration_is_paid
            else:
                payment_account_data_obj = PaymentAccountData(
                    worker=worker_obj,
                    financial_system_entity=financial_system_entity_obj,
                    account_number_where_the_remuneration_is_paid=account_number_where_the_remuneration_is_paid,
                )
            payment_account_data_obj.save()

        return JsonResponse({
            'success': True,
            # 'form': t.render(c),
        }, status=HTTPStatus.OK)


def get_subsidiary(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_set = Subsidiary.objects.all().order_by('id', 'serial')
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    return render(request, 'hrm/get_subsidiaries.html', {
        'subsidiary_obj': subsidiary_obj,
        'subsidiary_set': subsidiary_set,
        'districts': District.objects.all().select_related('province', 'province__department')
    })


def new_subsidiary(request):
    if request.method == 'POST':
        serial = request.POST.get('serial', '')
        name = request.POST.get('name', '')
        address = request.POST.get('address', '')
        district_id = request.POST.get('district_id', '')
        is_principal = request.POST.get('is_principal', '')
        district_obj = District.objects.get(id=int(district_id))
        _is_principal = False
        if is_principal:
            _is_principal = True

        Subsidiary.objects.create(serial=serial, name=name, address=address, is_subsidiary=True,
                                  business_name='INDUSTRIAS ANDERQUIN EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA',
                                  district=district_obj, is_main=_is_principal)

        return JsonResponse({
            'success': True,
            'message': 'Sede Creada'
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error contactar con sistemas'}, status=HTTPStatus.BAD_REQUEST)


def modal_subsidiary_edit(request):
    if request.method == 'GET':
        pk = int(request.GET.get('pk', ''))
        subsidiary_obj = Subsidiary.objects.get(id=pk)
        t = loader.get_template('hrm/subsidiary_update.html')
        c = ({
            'subsidiary_obj': subsidiary_obj,
            'districts': District.objects.all().select_related('province', 'province__department')
        })
        return JsonResponse({
            'form': t.render(c, request),
        })


@csrf_exempt
def update_subsidiary(request):
    if request.method == 'POST':
        subsidiary = request.POST.get('subsidiary', '')
        subsidiary_serial = request.POST.get('subsidiary_serial', '')
        subsidiary_name = request.POST.get('subsidiary_name', '')
        subsidiary_address = request.POST.get('subsidiary_address', '')
        district = request.POST.get('district', '')
        is_main = request.POST.get('is_main', '')
        _is_main = False
        if is_main:
            _is_main = True
        subsidiary_obj = Subsidiary.objects.get(id=subsidiary)
        district_obj = District.objects.get(id=int(district))
        subsidiary_obj.serial = subsidiary_serial
        subsidiary_obj.name = subsidiary_name
        subsidiary_obj.address = subsidiary_address
        subsidiary_obj.district = district_obj
        subsidiary_obj.is_main = _is_main
        subsidiary_obj.is_subsidiary = True
        subsidiary_obj.save()

        return JsonResponse({
            'success': True,
            'message': 'SEDE ACTUALIZADA'
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error contactar con sistemas'}, status=HTTPStatus.BAD_REQUEST)
