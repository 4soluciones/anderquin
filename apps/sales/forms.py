from django.utils.safestring import mark_safe
from django import forms
from .models import *


class FormClient(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('names', 'phone', 'email')


class FormSubsidiaryStore(forms.ModelForm):
    class Meta:
        model = SubsidiaryStore
        fields = ('subsidiary', 'name', 'category')
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Ingrese nombre',
                    'required': 'true',
                    'autocomplete': 'new-password',
                }
            ),
            'category': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
        }


class FormProduct(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('name',
                  'observation', 'code', 'stock_min',
                  'stock_max', 'product_family', 'product_brand', 'photo',
                  'barcode', 'valvule', 'product_subcategory',
                  'is_supply', 'is_merchandise', 'is_epp', 'is_equipment',
                  'is_machine', 'is_purchased', 'is_manufactured', 'is_imported', 'is_approved_by_osinergmin'
                  )
        labels = {
            'name': 'Nombre',
            'observation': 'Observacion',
            'code': 'Codigo',
            'stock_min': 'Stock Minimno',
            'stock_max': 'Stock Maximo',
            'product_family': 'Familia',
            'product_brand': 'Marca',
            'photo': 'Selecciona...',
            'barcode': 'Codigo de barras',
            'valvule': 'Tipo de Valvula',
            'product_subcategory': 'Subcategoria',
            'is_supply': 'Suministro',
            'is_merchandise': 'Mercancia',
            'is_epp': 'EPP',
            'is_equipment': 'Equipo',
            'is_machine': 'Maquina',
            'is_purchased': 'Comprado',
            'is_manufactured': 'Fabricado',
            'is_imported': 'Importado',
            'is_approved_by_osinergmin': 'GLP',
        }
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Ingrese nombre',
                    'required': 'true',
                    'autocomplete': 'new-password',
                }
            ),
            'observation': forms.Textarea(
                attrs={
                    'class': 'form-control form-control-sm',
                    'rows': 4,
                    'cols': 10,
                    'autocomplete': 'off',
                }
            ),
            'code': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'autocomplete': 'off',
                }
            ),
            'stock_min': forms.NumberInput(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'stock_max': forms.NumberInput(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'product_family': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'product_brand': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'photo': forms.FileInput(
                attrs={
                    'class': 'custom-file-input',
                    'onchange': 'readURL(this);',
                }
            ),
            'barcode': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'autocomplete': 'off',
                }
            ),
            'valvule': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),

            'product_subcategory': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'is_supply': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_merchandise': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_epp': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_equipment': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_machine': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_purchased': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_manufactured': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_imported': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_approved_by_osinergmin': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),

        }
