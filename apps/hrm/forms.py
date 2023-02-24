from django import forms
from .models import *
from datetime import datetime


class FormEmployee(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ('document_type', 'document_number',
                  'document_issuing_country', 'birthdate', 'paternal_last_name',
                  'maternal_last_name', 'names', 'gender', 'nationality',
                  'telephone_national_long_distance_code', 'telephone_number', 'email',
                  'address_1_road_type', 'address_1_road_name', 'address_1_road_number', 'address_1_department',
                  'address_1_interior', 'address_1_apple', 'address_1_lot', 'address_1_kilometer', 'address_1_block',
                  'address_1_stage', 'address_1_zone_type', 'address_1_zone_name', 'address_1_reference', 'address_1_district',
                  'address_2_road_type', 'address_2_road_name', 'address_2_road_number', 'address_2_department',
                  'address_2_interior', 'address_2_apple', 'address_2_lot', 'address_2_kilometer', 'address_2_block',
                  'address_2_stage', 'address_2_zone_type', 'address_2_zone_name', 'address_2_reference', 'address_2_district',
                  'essalud_assistance',
                  'n_license', 'license_type', 'license_expiration_date'
                  )
        labels = {
            'document_type': 'Tipo de documento (TD)',
            'document_number': 'Número de documento',
            'document_issuing_country': 'País emisor del documento',
            'birthdate': 'Fecha de nacimiento',
            'paternal_last_name': 'Apellido paterno',
            'maternal_last_name': 'Apellido materno',
            'names': 'Nombres',
            'gender': 'Sexo',
            'nationality': 'Nacionalidad',
            'telephone_national_long_distance_code': 'Teléfono - (CLDN)',
            'telephone_number': 'Teléfono – Número',
            'email': 'Correo electrónico',

            'address_1_road_type': 'Tipo de Vía',
            'address_1_road_name': 'Nombre de Vía',
            'address_1_road_number': 'Número de Vía',
            'address_1_department': 'Departamento',
            'address_1_interior': 'Interior',
            'address_1_apple': 'Manzana',
            'address_1_lot': 'Lote',
            'address_1_kilometer': 'Kilometro',
            'address_1_block': 'Block',
            'address_1_stage': 'Etapa',
            'address_1_zone_type': 'Tipo de Zona',
            'address_1_zone_name': 'Nombre de Zona',
            'address_1_reference': 'Referencia',
            'address_1_district': 'UBIGEO',

            'address_2_road_type': 'Tipo de Vía',
            'address_2_road_name': 'Nombre de Vía',
            'address_2_road_number': 'Número de Vía',
            'address_2_department': 'Departamento',
            'address_2_interior': 'Interior',
            'address_2_apple': 'Manzana',
            'address_2_lot': 'Lote',
            'address_2_kilometer': 'Kilometro',
            'address_2_block': 'Block',
            'address_2_stage': 'Etapa',
            'address_2_zone_type': 'Tipo de Zona',
            'address_2_zone_name': 'Nombre de Zona',
            'address_2_reference': 'Referencia',
            'address_2_district': 'UBIGEO',

            'essalud_assistance': 'Indicador Centro Asistencial EsSalud (solo asegurados al EsSalud)',

            'n_license': 'Numero de licencia',
            'license_type': 'Tipo de licencia',
            'license_expiration_date': 'Fecha de expiracion de licencia',

        }
        widgets = {
            'document_type': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                    'placeholder': 'Seleccione tipo'
                    # Set some placeholder
                    # 'data-placeholder': 'Autocomplete ...',
                    # Only trigger autocompletion after 3 characters have been typed
                    # 'data-minimum-input-length': 3,
                    # 'aria-describedby': 'nameHelpInline',
                }
            ),
            'document_number': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                    'placeholder': 'Ingrese nro dni',
                    'required': 'true',
                    'autocomplete': 'off',
                }
            ),
            'document_issuing_country': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'birthdate': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control form-control',
                    'type': 'date',
                    'pattern': '[0-9]{4}-[0-9]{2}-[0-9]{2}',
                    'required': 'true',
                }
            ),
            'paternal_last_name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                    'autocomplete': 'off',
                }
            ),
            'maternal_last_name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                    'autocomplete': 'off',
                }
            ),
            'names': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                    'required': 'true',
                    'autocomplete': 'off',
                }
            ),
            'gender': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'nationality': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                    'required': 'true',
                }
            ),
            'telephone_national_long_distance_code': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'telephone_number': forms.NumberInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_road_type': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_road_name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_road_number': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_department': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_interior': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_apple': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_lot': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_kilometer': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_block': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_stage': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_zone_type': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_zone_name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_reference': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_1_district': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),

            'address_2_road_type': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_road_name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_road_number': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_department': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_interior': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_apple': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_lot': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_kilometer': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_block': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_stage': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_zone_type': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_zone_name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_reference': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'address_2_district': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),

            'essalud_assistance': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'n_license': forms.TextInput(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'license_type': forms.Select(
                attrs={
                    'class': 'form-control form-control',
                }
            ),
            'license_expiration_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
        }


class FormWorker(forms.ModelForm):
    class Meta:
        model = Worker
        fields = (
            'employee', 'labor_regime',
            'educational_situation', 'occupation_private_sector', 'occupation_public_sector',
            'disability', 'cuspp', 'sctr_pension', 'contract_type',
            'subject_to_atypical_regime', 'subject_to_maximum_working_day', 'subject_to_night_time',
            'is_unionized', 'periodicity', 'initial_basic_remuneration', 'situation',
            'exempted_5th_category_rent', 'special_situation', 'payment_type',
            'occupational_category', 'agreement_to_avoid_double_taxation', 'ruc', 'user'
        )
        labels = {
            'employee': 'Empleado',
            'labor_regime': 'Régimen Laboral',
            'educational_situation': 'Situación Educativa',
            'occupation_private_sector': 'Ocupación',
            'occupation_public_sector': 'Ocupación',
            'disability': 'Discapacidad',
            'cuspp': 'CUSPP',
            'sctr_pension': 'SCTR Pensión',
            'contract_type': 'Tipo de contrato de trabajo/condición laboral',
            'subject_to_atypical_regime': 'Sujeto a régimen alternativo, acumulativo o atípico de jornada de trabajo y descanso',
            'subject_to_maximum_working_day': 'Sujeto a jornada de trabajo máxima',
            'subject_to_night_time': 'Sujeto a horario nocturno',
            'is_unionized': 'Es sindicalizado',
            'periodicity': 'Periodicidad de la remuneración o ingreso',
            'initial_basic_remuneration': 'Monto de la remuneración básica inicial de los trabajadores sujetos al régimen del D. Leg. 728',
            'situation': 'Situación ',
            'exempted_5th_category_rent': 'Rentas de 5ta categoría exoneradas (inciso e) del Art. 19 de la Ley del Impuesto a la Renta)',
            'special_situation': 'Situación especial del trabajador',
            'payment_type': 'Tipo de pago',
            'occupational_category': 'Categoría ocupacional del trabajador',
            'agreement_to_avoid_double_taxation': 'Convenio para evitar la doble tributación',
            'ruc': 'Número de RUC',
            'user': 'Usuario'
        }
        widgets = {
            'labor_regime': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'educational_situation': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'occupation_private_sector': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'occupation_public_sector': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'disability': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'cuspp': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'sctr_pension': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                    'disabled': 'disabled'
                }
            ),
            'contract_type': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'subject_to_atypical_regime': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'subject_to_maximum_working_day': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'subject_to_night_time': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_unionized': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'periodicity': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'initial_basic_remuneration': forms.NumberInput(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'situation': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'exempted_5th_category_rent': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'special_situation': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'payment_type': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'occupational_category': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'agreement_to_avoid_double_taxation': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'ruc': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'user': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                    'disabled': 'disabled',
                }
            )
        }
        help_texts = {
            'initial_basic_remuneration': 'Es aplicable a los trabajadores que inicien vínculo a partir de 01.08.2011 y cuyo régimen laboral corresponda a la actividad privada. ',
            'ruc': 'Solo para los CAS (tipo de trabajador = 67).',
        }


class FormPeriod(forms.ModelForm):
    class Meta:
        model = Period
        fields = (
            'worker',
            'category',
            'register_type',
            'start_or_restart_date',
            'ending_date',
            'indicator_of_the_type_of_registration',
            'reason_for_withdrawal',
            'worker_type',
            'health_insurance_regime',
            'pensioner_regime',
            'sctr_health',
            'eps_own_services'
        )
        labels = {
            'worker': 'Trabajador',
            'category': 'Categoría',
            'register_type': 'Tipo de registro',
            'start_or_restart_date': 'Fecha de inicio o reinicio',
            'ending_date': 'Fecha de fin',
            'indicator_of_the_type_of_registration': 'Indicador del tipo de registro a dar de alta o baja',
            'reason_for_withdrawal': 'Motivo de fin de período',
            'worker_type': 'Tipo de trabajador',
            'health_insurance_regime': 'Régimen de Aseg. De Salud',
            'pensioner_regime': 'Régimen Pensionario',
            'sctr_health': 'SCTR Salud',
            'eps_own_services': 'EPS/Servicios Propios'
        }
        widgets = {
            'worker': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'start_or_restart_date': forms.DateInput(
                format=('%Y-%m-%d'),
                # default=datetime.now(),
                attrs={
                    'class': 'form-control form-control',
                    'type': 'date',
                    'pattern': '[0-9]{4}-[0-9]{2}-[0-9]{2}',
                    'required': 'true',
                    # 'value': (datetime.now()).strftime("%Y-%m-%d"),
                }
            ),
            'reason_for_withdrawal': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'worker_type': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'health_insurance_regime': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'pensioner_regime': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'sctr_health': forms.Select(
                attrs={
                    'class': 'custom-select',
                    'disabled': 'disabled',
                }
            ),
        }


class FormEstablishment(forms.ModelForm):
    class Meta:
        model = Establishment
        fields = (
            'worker',
            'subsidiary',
            'ruc_own',
        )
        labels = {
            'worker': 'Trabajador',
            'subsidiary': 'Sede',
            'ruc_own': 'Ruc',
        }
        widgets = {
            'subsidiary': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
        }


class FormPaymentAccountData(forms.ModelForm):
    class Meta:
        model = PaymentAccountData
        fields = (
            'worker',
            'financial_system_entity',
            'account_number_where_the_remuneration_is_paid',
        )
        labels = {
            'worker': 'Trabajador',
            'financial_system_entity': 'Código de entidad financiera',
            'account_number_where_the_remuneration_is_paid': 'Cuenta de remuneración',
        }
        widgets = {
            'financial_system_entity': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'account_number_where_the_remuneration_is_paid': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            )
        }
