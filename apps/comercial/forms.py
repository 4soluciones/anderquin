from django import forms
from .models import *


class FormTruck(forms.ModelForm):
    class Meta:
        model = Truck
        fields = ['license_plate', 'num_axle', 'year', 'truck_model', 'drive_type', 'weight', 'contact_phone',
                  'certificate', 'serial', 'engine', 'chassis', 'color', 'fuel_type', 'owner', 'condition_owner',
                  'subsidiary', ]
        labels = {
            'license_plate': 'Placa',
            'num_axle': 'N de Ejes',
            'year': 'Año de Fabricacion',
            'truck_model': 'Modelos de Tracto',
            'drive_type': 'Tipo de Unidad',
            'weight': 'Capacidad de Carga',
            'contact_phone': 'Telefono de contacto',
            'certificate': 'Certificado',
            'serial': 'serie',
            'engine': 'motor',
            'chassis': 'chassis',
            'color': 'color',
            'fuel_type': 'Tipo de Combustible',
            'owner': 'Dueño',
            'condition_owner': 'Condicion de Propiedad',
            'subsidiary': 'Sucursal',

        }

        widgets = {
            'license_plate': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese el numero de placa',
                    'required': 'true',
                    'autocomplete': 'off',
                }
            ),
            'num_axle': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese N de ejes',
                    'type': 'number',
                    'autocomplete': 'off',
                }
            ),
            'year': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese  Año',
                    'required': 'true',
                    'type': 'number',
                    'autocomplete': 'off',
                }
            ),
            'truck_model': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Modelo',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'drive_type': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Tipo',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'weight': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Peso',
                    'autocomplete': 'off',
                }
            ),
            'contact_phone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Telefono de contacto',
                    'autocomplete': 'off',
                }
            ),
            'certificate': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese certificado',
                    'autocomplete': 'off',
                }
            ),
            'serial': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese serial',
                    'autocomplete': 'off',
                }
            ),

            'engine': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Numero  de motor',
                    'autocomplete': 'off',
                }
            ),
            'chassis': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Numero  de chasis',
                    'autocomplete': 'off',
                }
            ),
            'color': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Color',
                    'autocomplete': 'off',
                }
            ),
            'fuel_type': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Tipo de Combustible',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'owner': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Dueño',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'condition_owner': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Condicions',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'subsidiary': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
        }


class FormTowing(forms.ModelForm):
    class Meta:
        model = Towing
        fields = ['license_plate', 'num_axle', 'weight_towing', 'year', 'color', 'denomination', 'towing_model',
                  'towing_type', 'owner', 'condition_owner', ]
        labels = {
            'license_plate': 'Placa',
            'num_axle': 'N de Ejes',
            'weight_towing': 'Capacidad de Carga',
            'year': 'Año de Fabricacion',
            'color': 'Color',
            'denomination': 'Denominacion',
            'towing_model': 'Modelo de Furgon',
            'towing_type': 'Tipo de Furgon',
            'owner': 'Dueño',
            'condition_owner': 'Condicion de Propiedad',

        }

        widgets = {
            'license_plate': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese el numero de placa',
                    'required': 'true',
                    'autocomplete': 'off',
                }
            ),
            'num_axle': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese N de ejes',
                    'autocomplete': 'off',
                }
            ),
            'weight_towing': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Cantidad de Carga',
                    'type': 'number',
                    'autocomplete': 'off',
                }
            ),
            'year': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Año',
                    'type': 'number',
                    'autocomplete': 'off',
                }
            ),
            'color': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Color',
                    'autocomplete': 'off',
                }
            ),
            'denomination': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Denominacion',
                    'autocomplete': 'off',
                }
            ),
            'towing_model': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Modelo',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'towing_type': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Tipo',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'owner': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Dueño',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'condition_owner': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Tipo de Adquicicion',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
        }


class FormProgramming(forms.ModelForm):
    class Meta:
        model = Programming
        fields = ['departure_date', 'arrival_date', 'type', 'weight', 'truck', 'towing', 'subsidiary', 'observation',
                  'order', ]
        labels = {
            'departure_date': 'Fecha Programada',
            'arrival_date': 'Fecha de llegada',
            'type': 'Tipo',
            'weight': 'Peso',
            'truck': 'Tracto',
            'towing': 'Furgon',
            'subsidiary': 'Sucursal',
            'observation': 'Observacion',
            'order': 'Turno',

        }

        widgets = {
            'departure_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Fecha Programada',
                    'type': 'date',
                    'required': 'true',
                    'autocomplete': 'off',
                }
            ),
            'arrival_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Fecha de llegada',
                    'type': 'date',
                    'autocomplete': 'off',
                }
            ),
            'type': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Tipo',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'weight': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Peso',
                    'type': 'number',
                    'autocomplete': 'off',
                }
            ),
            'truck': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Tracto',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'towing': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Furgon',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'subsidiary': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Sucursal',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'observation': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Observacion',
                    'autocomplete': 'off',
                }
            ),
            'order': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Turno',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),

        }


class FormGuide(forms.ModelForm):
    class Meta:
        model = Guide
        fields = ['serial', 'code', 'status', 'minimal_cost', 'observation', 'client']
        labels = {'serial': 'Serie',
                  'code': 'Codigo',
                  'status': 'Estado',
                  'minimal_cost': 'Costo minimo',
                  'observation': 'Observaciones',
                  'client': 'Cliente',
                  }
