from django.utils.safestring import mark_safe
from django import forms
from .models import *


class FormClient(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('names', 'phone', 'email', 'price_type')
        widgets = {
            'price_type': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
        }


class FormPriceType(forms.ModelForm):
    class Meta:
        model = PriceType
        fields = ('name', 'description', 'is_enabled')
        labels = {
            'name': 'Nombre',
            'description': 'Descripción',
            'is_enabled': 'Habilitado',
        }
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Ingrese nombre',
                    'required': 'true',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control form-control-sm',
                    'rows': 3,
                }
            ),
            'is_enabled': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
        }


class FormProductPrice(forms.ModelForm):
    class Meta:
        model = ProductPrice
        fields = ('price_type', 'product_detail', 'price', 'is_enabled')
        labels = {
            'price_type': 'Tipo de Precio',
            'product_detail': 'Presentación',
            'price': 'Precio',
            'is_enabled': 'Habilitado',
        }
        widgets = {
            'price_type': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'product_detail': forms.Select(
                attrs={
                    'class': 'form-control form-control-sm',
                }
            ),
            'price': forms.NumberInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'step': '0.01',
                }
            ),
            'is_enabled': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
        }


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
                  'observation', 'code', 'internal_code', 'stock_min',
                  'stock_max', 'weight', 'product_family', 'product_brand', 'photo',
                  'barcode', 'product_subcategory',
                  'is_enabled', 'is_supply', 'is_merchandise',
                  'is_purchased', 'is_manufactured',
                  )
        labels = {
            'name': 'Nombre',
            'observation': 'Observacion',
            'code': 'Codigo',
            'internal_code': 'Codigo Interno',
            'stock_min': 'Stock Minimno',
            'stock_max': 'Stock Maximo',
            'weight': 'Peso (Unidad)',
            'product_family': 'Familia',
            'product_brand': 'Marca',
            'photo': 'Selecciona...',
            'barcode': 'Codigo de barras',
            # 'valvule': 'Tipo de Valvula',
            'product_subcategory': 'Subcategoria',
            'is_enabled': 'Activo',
            'is_supply': 'Suministro',
            'is_merchandise': 'Mercancia',
            # 'is_epp': 'EPP',
            # 'is_equipment': 'Equipo',
            # 'is_machine': 'Maquina',
            'is_purchased': 'Comprado',
            'is_manufactured': 'Fabricado',
            # 'is_imported': 'Importado',
            # 'is_approved_by_osinergmin': 'GLP',
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
            'internal_code': forms.TextInput(
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
            'weight': forms.NumberInput(
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
                    'class': 'form-control form-control-sm text-uppercase',
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
            # 'valvule': forms.Select(
            #     attrs={
            #         'class': 'form-control form-control-sm',
            #     }
            # ),

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
            'is_enabled': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            'is_merchandise': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
            # 'is_epp': forms.CheckboxInput(
            #     attrs={
            #         'class': 'form-check-input',
            #     }
            # ),
            # 'is_equipment': forms.CheckboxInput(
            #     attrs={
            #         'class': 'form-check-input',
            #     }
            # ),
            # 'is_machine': forms.CheckboxInput(
            #     attrs={
            #         'class': 'form-check-input',
            #     }
            # ),
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
            # 'is_imported': forms.CheckboxInput(
            #     attrs={
            #         'class': 'form-check-input',
            #     }
            # ),
            # 'is_approved_by_osinergmin': forms.CheckboxInput(
            #     attrs={
            #         'class': 'form-check-input',
            #     }
            # ),

        }
