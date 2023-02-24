from django.utils.translation import gettext_lazy as _
from django import forms
from .models import *


class FormSubsidiary(forms.ModelForm):
    # name = forms.CharField(
    #     max_length=200,
    #     label='Your subsidiary',
    #     widget=forms.TextInput(
    #         attrs={
    #             'class': 'form-control',
    #             'placeholder': 'Ingrese el nombre de la subsidiaria'
    #         }
    #     ),
    #     help_text='Write here your message!'
    # )
    # address = forms.CharField(max_length=100)
    # serie = forms.CharField(
    #     max_length=3,
    #     required=True
    # )
    class Meta:
        model = Subsidiary
        fields = ['name', 'address', 'serie']
        labels = {
            'name': 'Nombre de la subsidiaria',
            'address': 'Direccion',
            'serie': 'Serie',
        }
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'class': 'form-control is-invalid',
                    'placeholder': 'Ingrese el nombre de la subsidiaria',
                    # 'aria-describedby': 'nameHelpInline',
                    'autocomplete': 'off',
                }
            ),
            'address': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese la direccion',
                    # 'aria-describedby': 'addressHelpInline',
                    'autocomplete': 'off',
                }
            ),
            'serie': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese una serie',
                    # 'aria-describedby': 'serieHelpInline',
                    'autocomplete': 'off',
                }
            )
        }
        help_texts = {
            'name': 'Must be 3-200 characters.',
        }
        error_messages = {
            'name': {
                'max_length': _("This writer's name is too long."),
                'required': 'my required msg..',
                'unique': 'must be unique',
            }
        }


class FormCategory(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'description', 'subsidiary')
        '''
        label = {
            'name':'Nombre de la categoria',
            'description': 'Descripcion',
            'subsidiary': 'Sucursal'
        }
        widgets = {
            'name': forms.TextInput(
                attrs = {
                    'class': 'form-control',
                    'placeholder': 'Ingrese nombre de la categoria'
                }
            ),
            'description': forms.TextInput(
                attrs = {
                    'class': 'form-control',
                    'placeholder': 'Ingrese descripcion'
                }
            ),

            'subsidiary': forms.ComboField(
                attrs = {
                    'class':'form-control'
                }
            )
        }
        '''


class FormSubcategory(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ('name', 'description', 'category')


class FormDish(forms.ModelForm):
    class Meta:
        model = Dish
        fields = ('name', 'image', 'price', 'subcategory', 'quantity')
