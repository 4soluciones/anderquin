from django.shortcuts import render, redirect  # nos permite renderizar plantillas de forma cómoda
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import View, TemplateView, ListView, UpdateView, CreateView, DeleteView
from django.urls import reverse_lazy
from datetime import datetime  # Este import lo hacemos para poder usarlo en la func current_datetime

from django.contrib.auth import authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import JsonResponse
from http import HTTPStatus
from django.template import loader
from django.forms.models import model_to_dict

from apps.dishes.models import *
from apps.dishes.forms import *
from apps.hrm.models import DocumentType

import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import ImageFieldFile
# serialize an ImageField in Django


class ExtendedEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, ImageFieldFile):
            return str(o)
        else:
            return super().default(o)


def current_datetime(request):
    return render(request, 'hora.html', {'current_date': str(datetime.now())})


class Dashboard(TemplateView):
    # template_name = 'dashboard.html'
    # template_name = 'vetstore/home.html'
    template_name = 'hrm/main.html'


class SubsidiaryList(View):
    model = Subsidiary
    form_class = FormSubsidiary
    template_name = 'dishes/subsidiary_list.html'

    def get_queryset(self):
        return self.model.objects.filter(status=True)

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['subsidiaries'] = self.get_queryset()  # agregamos la consulta al contexto
        contexto['form'] = self.form_class
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class SubsidiaryCreate(CreateView):
    model = Subsidiary
    form_class = FormSubsidiary
    template_name = 'dishes/subsidiary_create.html'
    success_url = reverse_lazy('dishes:subsidiary_list')


class SubsidiaryUpdate(UpdateView):
    model = Subsidiary
    form_class = FormSubsidiary
    template_name = 'dishes/subsidiary_update.html'
    success_url = reverse_lazy('dishes:subsidiary_list')


class SubsidiaryDelete(DeleteView):
    model = Subsidiary
    template_name = "dishes/subsidiary_confirm_delete.html"

    def post(self, request, pk, *args, **kwargs):
        object = Subsidiary.objects.get(id=pk)
        object.status = False
        object.save()
        return redirect('dishes:subsidiary_list')


class CategoryList(View):
    model = Category
    form_class = FormCategory
    template_name = 'dishes/category_list.html'

    def get_queryset(self):
        return self.model.objects.filter(status=True)

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['categories'] = self.get_queryset()  # agregamos la consulta al contexto
        contexto['form'] = self.form_class
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class CategoryCreate(CreateView):
    model = Category
    form_class = FormCategory
    template_name = 'dishes/category_create.html'
    success_url = reverse_lazy('dishes:category_list')


class CategoryUpdate(UpdateView):
    model = Category
    form_class = FormCategory
    template_name = 'dishes/category_update.html'
    success_url = reverse_lazy('dishes:category_list')


class CategoryDelete(DeleteView):
    model = Category
    template_name = "dishes/category_confirm_delete.html"

    def post(self, request, pk, *args, **kwargs):
        object = Category.objects.get(id=pk)
        object.status = False
        object.save()
        return redirect('dishes:category_list')


class SubcategoryList(View):
    model = Subcategory
    form_class = FormSubcategory
    template_name = 'dishes/subcategory_list.html'

    def get_queryset(self):
        return self.model.objects.filter(status=True)

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['subcategories'] = self.get_queryset()  # agregamos la consulta al contexto
        contexto['form'] = self.form_class
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class SubcategoryCreate(CreateView):
    model = Subcategory
    form_class = FormSubcategory
    template_name = 'dishes/subcategory_create.html'
    success_url = reverse_lazy('dishes:subcategory_list')


class SubcategoryUpdate(UpdateView):
    model = Subcategory
    form_class = FormSubcategory
    template_name = 'dishes/subcategory_update.html'
    success_url = reverse_lazy('dishes:subcategory_list')


class SubcategoryDelete(DeleteView):
    model = Subcategory
    template_name = "dishes/subcategory_confirm_delete.html"

    def post(self, request, pk, *args, **kwargs):
        object = Subcategory.objects.get(id=pk)
        object.status = False
        object.save()
        return redirect('dishes:subcategory_list')


class DishList(View):
    model = Dish
    form_class = FormDish
    template_name = 'dishes/dish_list.html'

    def get_queryset(self):
        return self.model.objects.filter(status=True).order_by("id")

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['dishes'] = self.get_queryset()  # agregamos la consulta al contexto
        contexto['form'] = self.form_class
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class JsonDishList(View):
    def get(self, request):
        dishes = Dish.objects.filter(status=True).order_by("id")
        # dishes = list(Dish.objects.all().values())
        # data = dict()
        # data['dishes'] = dishes
        t = loader.get_template('dishes/dish_grid_list.html')
        c = ({'dishes': dishes})
        return JsonResponse({'result': t.render(c)})
        # return JsonResponse(data)
        # return render(request, self.template_name, data)


class JsonDishCreate(CreateView):
    model = Dish
    form_class = FormDish
    template_name = 'dishes/dish_create.html'

    def post(self, request):
        # Recibe como parámetro una representación de un diccionario
        data = dict()
        form = FormDish(request.POST, request.FILES)
        # print(request.POST)
        # print(request.FILES)
        if form.is_valid():
            dish = form.save()
            # converting a database model to a dictionary...
            data['dish'] = model_to_dict(dish)
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


class JsonDishUpdate(UpdateView):
    model = Dish
    form_class = FormDish
    template_name = 'dishes/dish_update.html'

    def post(self, request, pk):
        data = dict()
        dish = self.model.objects.get(pk=pk)
        # form = SnapForm(request.POST, request.FILES, instance=instance)
        form = self.form_class(instance=dish, data=request.POST, files=request.FILES)
        if form.is_valid():
            dish = form.save()
            data['dish'] = model_to_dict(dish)
            result = json.dumps(data, cls=ExtendedEncoder)
            response = JsonResponse(result, safe=False)
            response.status_code = HTTPStatus.OK
        else:
            data['error'] = "form not valid!"
            data['form_invalid'] = form.errors
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


class JsonDishDelete(DeleteView):
    model = Dish
    template_name = "dishes/dish_confirm_delete.html"

    def post(self, request, pk):
        data = dict()
        dish = self.model.objects.get(pk=pk)
        if dish:
            dish.status = False
            dish.save()
            # dish.delete()
            data['message'] = "Dish deleted!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.OK
        else:
            data['message'] = "Error!"
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
        return response


def get_dishes(request):
    if request.method == 'GET':
        try:
            dish_id = request.GET.get('search', 0)
            dish = Dish.objects.get(pk=dish_id)
            t = loader.get_template('result.html')
            c = ({'dish': dish})
            return JsonResponse({'result': t.render(c)})
        except Dish.DoesNotExist:
            t = loader.get_template('result.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe el plato.'})
            return JsonResponse({'success': False, 'result': t.render(c)})
    t = loader.get_template('result.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'result': t.render(c)})
