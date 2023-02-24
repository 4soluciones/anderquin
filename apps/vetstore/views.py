from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from datetime import date, datetime, timedelta, time
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.views.generic import View, TemplateView, ListView, UpdateView, CreateView, DeleteView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse, HttpResponseRedirect
from apps.vetstore.models import *
from django.template import loader
from django.http import JsonResponse
from django.db.models import Q, F, Sum
import json
import csv
# Create your views here.


class Home(TemplateView):
    template_name = 'vetstore/home.html'


def get_page(request):
    print("LLEGO AQUI")
    if request.method == 'GET':
        data_url = request.GET.get('data_url', '')
        if data_url == 'home':

            t = loader.get_template('vetstore/home.html')
            c = ({
                'title': 'Inicio',
            })
            return JsonResponse({'success': True, 'page': t.render(c), 'message': 'Bienvenido ...'})
        else:
            if data_url == 'products':
                now = datetime.now()
                # products = Product.objects.all()
                products = Product.objects.filter(
                    update_at__year=now.year, update_at__month=now.month, update_at__day=now.day).order_by('-update_at')

                print(products)
                # employee = Employee.objects.get(user=request.user)
                # role = employee.role.first().code
                role = "ADM"
                t3 = loader.get_template('vetstore/product-list.html')

                c3 = ({'products': products, 'role': role})

                t4 = loader.get_template('vetstore/product-register-form.html')
                c4 = ({'formatted_time': datetime.now()})

                t = loader.get_template('vetstore/form-product.html')
                c = ({'title': 'Gestionar productos', 'role': role})

                t2 = loader.get_template('vetstore/alerts.html')
                c2 = ({'info': True, 'title': 'Nota', 'message': 'Gestionar productos'})
                return JsonResponse({'success': True, 'page': t.render(c), 'alert': t2.render(c2), 'list': t3.render(c3), 'form': t4.render(c4), })
            else:
                if data_url == 'purchases':
                    print(data_url)

                    employee = Employee.objects.get(user=request.user)
                    branch_office = employee.branch_office

                    now = datetime.now()
                    purchases = Purchase.objects.filter(
                        created_at__year=now.year, created_at__month=now.month, created_at__day=now.day).order_by('-created_at')

                    t3 = loader.get_template('vetstore/purchase-list.html')
                    c3 = ({'purchases': purchases})

                    t4 = loader.get_template('vetstore/purchase-register-form.html')
                    c4 = ({'formatted_time': datetime.now(), 'branch_office_id': branch_office.id})

                    t = loader.get_template('vetstore/form-purchase.html')
                    c = ({'title': 'Gestionar compras'})
                    return JsonResponse({'success': True, 'page': t.render(c), 'list': t3.render(c3), 'form': t4.render(c4)})
                else:
                    if data_url == 'sales':
                        print(data_url)

                        employee = Employee.objects.get(user=request.user)
                        branch_office = employee.branch_office
                        role = employee.role.first().code

                        now = datetime.now()
                        sales = Sales.objects.filter(branch_office_id=branch_office.id).filter(status='A').filter(
                            created_at__date__year=now.year, created_at__date__month=now.month, created_at__date__day=now.day).order_by('-created_at')

                        charged_sum = sales.aggregate(Sum('charged'))
                        received_sum = sales.aggregate(Sum('received'))
                        turned_sum = sales.aggregate(Sum('turned'))
                        sales_gain_obtained_sum = 0
                        sales_gain_estimated_sum = 0
                        sales_total_discount_turned_sum = 0

                        for sale in sales:
                            for detail in sale.detail_sales.all():
                                sales_gain_obtained_sum += detail.profit_per_product_in_sales_obtained
                                sales_gain_estimated_sum += detail.profit_per_product_in_sales_estimated
                                sales_total_discount_turned_sum += detail.discount_per_product_in_sales

                        t3 = loader.get_template('vetstore/sales-list.html')
                        c3 = ({
                            'role': role,
                            'sales': sales,
                            'charged_sum': charged_sum,
                            'received_sum': received_sum,
                            'turned_sum': turned_sum,
                            'sales_gain_obtained_sum': sales_gain_obtained_sum,
                            'sales_gain_estimated_sum': sales_gain_estimated_sum,
                            'sales_total_discount_turned_sum': sales_total_discount_turned_sum
                        })

                        customer = Customer.objects.get(pk=2)
                        waypays = WayPay.objects.all()
                        t4 = loader.get_template('vetstore/sales-register-form.html')
                        c4 = ({'formatted_time': datetime.now(), 'waypays': waypays,
                               'customer': customer, 'branch_office_id': branch_office.id})

                        t = loader.get_template('vetstore/form-sales.html')
                        c = ({'title': 'Gestionar ventas', 'date': datetime.now(),
                              'branch_office_id': branch_office.id, 'role': role})
                        return JsonResponse({'success': True, 'page': t.render(c), 'list': t3.render(c3), 'form': t4.render(c4)})
                    else:
                        if data_url == 'categories':
                            print(data_url)
                            categories = Category.objects.all()
                            # categories = Category.objects.filter(name__icontains=str(search))
                            results = []
                            for category in categories:
                                results.append({
                                    'id': category.id,
                                    'name': category.name,
                                    'comment': category.comment,
                                    'parent': category.parent
                                })
                            # print 'results: ', results
                            t = loader.get_template('vetstore/category-list.html')
                            c = ({'title': 'Gestionar categorías', 'categories': categories})
                            return JsonResponse({'success': True, 'page': t.render(c), 'message': 'Bienvenido ...'})
                        else:
                            if data_url == 'reports':
                                print(data_url)
                                products = Product.objects.filter(
                                    current_inventory__lte=F('minimum_inventory'))
                                t = loader.get_template('vetstore/report.html')
                                c = ({'title': 'Gestionar reportes', 'products': products})

                                return JsonResponse({'success': True, 'page': t.render(c), 'message': 'Bienvenido ...'})
                            else:
                                if data_url == 'suppliers':
                                    print(data_url)
                                    suppliers = Supplier.objects.all()
                                    t3 = loader.get_template('vetstore/supplier-list.html')
                                    c3 = ({'suppliers': suppliers})

                                    t4 = loader.get_template('vetstore/supplier-register-form.html')
                                    c4 = ({'formatted_time': datetime.now()})

                                    t = loader.get_template('vetstore/form-supplier.html')
                                    c = ({'title': 'Gestionar proveedores'})
                                    return JsonResponse(
                                        {'success': True, 'page': t.render(c), 'list': t3.render(c3), 'form': t4.render(c4)})
                                else:
                                    if data_url == 'attendances':
                                        print(data_url)

                                        employee = Employee.objects.get(user=request.user)
                                        role = employee.role.first().code
                                        print('role: ', role)

                                        now = datetime.now()

                                        attendances = Attendance.objects.filter(
                                            date_assigned__year=now.year, date_assigned__month=now.month, date_assigned__day=now.day)
                                        # attendances = Attendance.objects.all()
                                        t3 = loader.get_template('vetstore/attendance-list.html')
                                        c3 = ({'attendances': attendances, 'role': role})

                                        t4 = loader.get_template(
                                            'vetstore/attendance-register-form.html')
                                        c4 = ({'formatted_time': datetime.now()})

                                        t = loader.get_template('vetstore/form-attendance.html')
                                        c = ({'title': 'Gestionar asistencias',
                                              'date': datetime.now(), 'role': role})
                                        return JsonResponse(
                                            {'success': True, 'page': t.render(c), 'list': t3.render(c3), 'form': t4.render(c4)})
                                    else:
                                        if data_url == 'expenses':
                                            print(data_url)
                                            now = datetime.now()
                                            expenses = Expense.objects.filter(
                                                created_at__year=now.year, created_at__month=now.month, created_at__day=now.day)
                                            t3 = loader.get_template('vetstore/expense-list.html')
                                            c3 = ({'expenses': expenses})

                                            t4 = loader.get_template(
                                                'vetstore/expense-register-form.html')
                                            c4 = ({'formatted_time': datetime.now()})

                                            t = loader.get_template('vetstore/form-expense.html')
                                            c = ({'title': 'Gestionar egresos'})
                                            return JsonResponse(
                                                {'success': True, 'page': t.render(c), 'list': t3.render(c3), 'form': t4.render(c4)})
                                        else:
                                            if data_url == 'product_return':
                                                print(data_url)
                                                now = datetime.now()

                                                devolutions = ProductReturn.objects.filter(return_date__year=now.year,
                                                                                           return_date__month=now.month,
                                                                                           return_date__day=now.day).order_by('-return_date')

                                                t3 = loader.get_template(
                                                    'vetstore/product-return-list.html')
                                                c3 = ({'devolutions': devolutions})

                                                t4 = loader.get_template(
                                                    'vetstore/product-return-register-form.html')
                                                c4 = ({'formatted_time': datetime.now()})

                                                t = loader.get_template(
                                                    'vetstore/form-product-return.html')
                                                c = ({'title': 'Gestionar devoluciones'})
                                                return JsonResponse(
                                                    {'success': True, 'page': t.render(c), 'list': t3.render(c3), 'form': t4.render(c4)})
                                            else:
                                                if data_url == 'data_group':

                                                    sales = Sales.objects.all().order_by('sale_date')
                                                    purchases = Purchase.objects.all()

                                                    t3 = loader.get_template(
                                                        'vetstore/group-payments.html')
                                                    c3 = ({'formatted_time': datetime.now()})

                                                    t = loader.get_template(
                                                        'vetstore/form-group-payment.html')
                                                    formatted_time = timezone.now()
                                                    print(formatted_time)
                                                    c = ({'title': 'Entrada y salidas',
                                                          'date': formatted_time})
                                                    return JsonResponse(
                                                        {'success': True, 'page': t.render(c), })
                                                else:

                                                    if data_url == 'brands':
                                                        print(data_url)

                                                        brands = Brand.objects.all()
                                                        employee = Employee.objects.get(
                                                            user=request.user)
                                                        role = employee.role.first().code
                                                        print('role: ', role)
                                                        t3 = loader.get_template(
                                                            'vetstore/brand-list.html')

                                                        c3 = ({'brands': brands, 'role': role})

                                                        t4 = loader.get_template(
                                                            'vetstore/brand-register-form.html')
                                                        c4 = ({'formatted_time': datetime.now()})

                                                        t = loader.get_template(
                                                            'vetstore/form-brand.html')
                                                        c = (
                                                            {'title': 'Gestion de marcas', 'role': role})
                                                        return JsonResponse(
                                                            {'success': True, 'page': t.render(c), 'list': t3.render(c3), 'form': t4.render(c4)})
                                                    else:

                                                        if data_url == 'employees':
                                                            print(data_url)
                                                            employees = Employee.objects.all()
                                                            employee = Employee.objects.get(
                                                                user=request.user)
                                                            role = employee.role.first().code
                                                            print('role: ', role)
                                                            t = loader.get_template(
                                                                'vetstore/employee-list.html')
                                                            c = (
                                                                {'employees': employees, 'title': 'Gestión de empleados', 'role': role})
                                                            return JsonResponse(
                                                                {'success': True, 'page': t.render(c)})
    return HttpResponseBadRequest('Solicitud invalida, por favor regrese a la página anterior.')


@csrf_exempt
def get_criteria_product(request):
    if request.method == 'POST':
        mode_product_name_selected = str(request.POST.get('mode-product-name-selected', ''))
        criteria_product_name = str(request.POST.get('criteria-product-name', ''))

        mode_product_barcode_selected = str(request.POST.get('mode-product-barcode-selected', ''))
        criteria_product_barcode = str(request.POST.get('criteria-product-barcode', ''))

        mode_batch_barcode_selected = str(request.POST.get('mode-batch-barcode-selected', ''))
        criteria_batch_barcode = str(request.POST.get('criteria-batch-barcode', ''))

        mode_branch_office_id_selected = str(request.POST.get('mode-branch-office-id-selected', ''))
        criteria_branch_office_id = str(request.POST.get('criteria-branch-office-id', ''))

        mode_brand_id_selected = str(request.POST.get('mode-brand-id-selected', ''))
        criteria_brand_id = str(request.POST.get('criteria-brand-id', ''))

        mode_category_id_selected = str(request.POST.get('mode-category-id-selected', ''))
        criteria_category_id = str(request.POST.get('criteria-category-id', ''))

        has_stock = str(request.POST.get('has-stock', ''))

        products = Product.objects.all()

        if len(criteria_product_name) > 0:
            if mode_product_name_selected == 'CONTAINS':
                products = products.filter(name__icontains=criteria_product_name)
                print('products.count(): ', products.count())
            else:
                if mode_product_name_selected == 'DOES_NOT_CONTAIN':
                    products = products.exclude(name__icontains=criteria_product_name)
                else:
                    if mode_product_name_selected == 'EQUALS':
                        products = products.filter(name__exact=criteria_product_name)
                    else:
                        if mode_product_name_selected == 'NOT_EQUALS':
                            products = products.exclude(name__exact=criteria_product_name)

        if len(criteria_product_barcode) > 0:
            if mode_product_barcode_selected == 'CONTAINS':
                products = products.filter(barcode__icontains=criteria_product_barcode)
                # print 'products.count(): ', products.count()
            else:
                if mode_product_barcode_selected == 'DOES_NOT_CONTAIN':
                    products = products.exclude(barcode__icontains=criteria_product_barcode)
                else:
                    if mode_product_barcode_selected == 'EQUALS':
                        products = products.filter(barcode__exact=criteria_product_barcode)
                    else:
                        if mode_product_barcode_selected == 'NOT_EQUALS':
                            products = products.exclude(barcode__exact=criteria_product_barcode)

        if len(criteria_batch_barcode) > 0:
            if mode_batch_barcode_selected == 'CONTAINS':
                products = products.filter(batches__barcode__icontains=criteria_batch_barcode)
                # print 'products.count(): ', products.count()
            else:
                if mode_batch_barcode_selected == 'DOES_NOT_CONTAIN':
                    products = products.exclude(batches__barcode__icontains=criteria_batch_barcode)
                else:
                    if mode_batch_barcode_selected == 'EQUALS':
                        products = products.filter(batches__barcode__exact=criteria_batch_barcode)
                    else:
                        if mode_batch_barcode_selected == 'NOT_EQUALS':
                            products = products.exclude(
                                batches__barcode__exact=criteria_batch_barcode)

        if len(criteria_branch_office_id) > 0 and criteria_branch_office_id != '0':
            if mode_branch_office_id_selected == 'EQUALS':
                products = products.filter(
                    acquisitiondetail__purchase__employee__branch_office_id=criteria_branch_office_id)
            else:
                if mode_branch_office_id_selected == 'NOT_EQUALS':
                    products = products.exclude(
                        acquisitiondetail__purchase__employee__branch_office_id=criteria_branch_office_id)

        if len(criteria_brand_id) > 0 and criteria_brand_id != '0':
            if mode_brand_id_selected == 'EQUALS':
                products = products.filter(brand_id=criteria_brand_id)
            else:
                if mode_brand_id_selected == 'NOT_EQUALS':
                    products = products.exclude(brand_id=criteria_brand_id)

        if len(criteria_category_id) > 0 and criteria_category_id != '0':
            if mode_category_id_selected == 'EQUALS':
                products = products.filter(category_id=criteria_category_id)
            else:
                if mode_category_id_selected == 'NOT_EQUALS':
                    products = products.exclude(category_id=criteria_category_id)

        if len(has_stock) > 0:
            if has_stock == 'N':
                products = products.filter(status="S")
            else:
                if has_stock == 'S':
                    products = products.filter(status="A")
                else:
                    if has_stock == 'A':
                        products = products.filter(Q(status="S") | Q(status="A"))

        # employee = Employee.objects.get(user=request.user)
        # role = employee.role.first().code
        role = "ADM"

        t = loader.get_template('vetstore/product-list.html')
        c = ({'products': products, 'role': role})

        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'success': True, 'title': '¡Bien hecho!', 'message': 'Busqueda exitosa.'})

        return JsonResponse({'success': True, 'list': t.render(c), 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def product_registration(request):
    if request.method == 'POST':

        wholesale_request = request.POST.get('wholesales', '')
        data_wr = json.loads(wholesale_request)
        # rows = data_wr['Rows']
        brand_id = int(request.POST.get('brand', 0))

        try:
            brand = Brand.objects.get(id=brand_id)
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No existe marca.'})

        category_id = int(request.POST.get('category-id', 0))

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe la categoría.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        code = '000'
        if category_id < 1000:

            if category_id < 100:

                if category_id < 10:

                    code = '00', str(category_id)
                else:

                    code = '0', str(category_id)
            else:

                code = str(category_id)
        else:

            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'excedio el numero de categorías.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        if brand_id < 1000:

            if brand_id < 100:

                if brand_id < 10:

                    code += '00', str(brand_id)
                else:

                    code += '0', str(brand_id)
            else:

                code += str(brand_id)
        else:

            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'excedio el numero de marcas.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        code = "".join(code)

        data = {
            'name': request.POST.get('name', ''),
            'label': request.POST.get('label', ''),
            'factory_barcode': request.POST.get('factory-barcode', ''),
            'comment': request.POST.get('comment', ''),
            'sale_price': request.POST.get('sale-price', 0),
            'pass_price': request.POST.get('pass-price', 0),
            'discount_price': request.POST.get('discount-price', 0),
            'minimum_inventory': request.POST.get('minimum-inventory', 0),
            # 'barcode': 1,
            'brand': brand,
            'category': category
        }
        product = Product.objects.create(**data)

        barcode = str(product.id), code
        barcode = "".join(barcode)

        product.barcode = barcode
        product.save()

        filepath = request.FILES.get('image', False)
        if filepath:
            product.image = request.FILES['image']
            product.image_thumbnail = request.FILES['image']
            product.save()

        for r in data_wr['Rows']:
            if float(r['Price']) > 0 and int(r['Quantity']) > 0:
                wholesale_data = {
                    'price': float(r['Price']),
                    'quantity': int(r['Quantity']),
                    'product': product
                }
                wholesale = Wholesale.objects.create(**wholesale_data)
                wholesale.save()

        now = datetime.now()
        products = Product.objects.filter(update_at__year=now.year, update_at__month=now.month,
                                          update_at__day=now.day).order_by('-update_at')
        employee = Employee.objects.get(user=request.user)
        role = employee.role.first().code
        t3 = loader.get_template('vetstore/product-list.html')
        c3 = ({'products': products, 'role': role})

        t = loader.get_template('vetstore/alerts.html')
        c = ({'success': True, 'title': '¡Bien hecho!',
              'message': 'Los datos se han registrado correctamente.'})
        return JsonResponse({'success': True, 'alert': t.render(c), 'list': t3.render(c3)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def get_product(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe el producto.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        wholesales = Wholesale.objects.filter(product_id=pk)
        t = loader.get_template('vetstore/product-update-form.html')
        c = ({'product': product, 'wholesales': wholesales})
        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'info': True, 'title': 'Atento',
               'message': 'Verifique, antes de almacenar las modificaciones hechas a los datos.'})
        return JsonResponse({
            'success': True,
            'formupdate': t.render(c),
            'alert': t2.render(c2)
        })

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def product_update(request):
    if request.method == 'POST':

        id = request.POST.get('product-id', 0)

        try:
            product = Product.objects.get(pk=int(id))
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No existe el producto.'})

        wholesale_request = request.POST.get('wholesales', '')
        data_wr = json.loads(wholesale_request)
        for old_data_wr in data_wr['OldRows']:
            old_w = Wholesale.objects.get(id=int(old_data_wr['Id']))
            if str(old_data_wr['Status']) == 'R':
                old_w.delete()
            else:
                if str(old_data_wr['Status']) == 'U':
                    old_w.price = float(old_data_wr['Price'])
                    old_w.quantity = float(old_data_wr['Quantity'])
                    old_w.save()

        for r in data_wr['Rows']:
            if str(r['Status']) == 'N' and float(r['Price']) > 0 and int(r['Quantity']) > 0:
                wholesale_data = {
                    'price': float(r['Price']),
                    'quantity': int(r['Quantity']),
                    'product': product
                }
                wholesale = Wholesale.objects.create(**wholesale_data)
                wholesale.save()

        brand_id = request.POST.get('brand-id', 0)

        if int(brand_id) == 0:
            brand = None
        else:
            brand = Brand.objects.get(pk=int(brand_id))

        category_id = request.POST.get('category-id', '')

        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe categoria.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        product.name = str(request.POST.get('name', ''))
        product.label = str(request.POST.get('label', ''))
        product.factory_barcode = str(request.POST.get('factory-barcode', ''))
        product.comment = str(request.POST.get('comment', ''))
        product.sale_price = float(request.POST.get('sale-price', 0))
        product.pass_price = float(request.POST.get('pass-price', 0))
        product.discount_price = float(request.POST.get('discount-price', 0))
        product.minimum_inventory = int(request.POST.get('minimum-inventory', 0))
        # product.status = str(request.POST.get('status', ''))
        product.brand = brand
        product.category = category

        filepath = request.FILES.get('image', False)
        if filepath:
            product.image = request.FILES['image']
            product.image_thumbnail = request.FILES['image']
        else:
            print('invalid image')

        product.save()

        now = datetime.now()
        products = Product.objects.filter(update_at__year=now.year, update_at__month=now.month,
                                          update_at__day=now.day).order_by('-update_at')
        employee = Employee.objects.get(user=request.user)
        role = employee.role.first().code
        t3 = loader.get_template('vetstore/product-list.html')
        c3 = ({'products': products, 'role': role})

        t = loader.get_template('vetstore/alerts.html')
        c = ({'success': True, 'title': '¡Bien hecho!',
              'message': 'Los datos se han actualizado correctamente.'})
        return JsonResponse({'success': True, 'alert': t.render(c), 'list': t3.render(c3)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def category_list(request):
    if request.is_ajax():
        search = request.GET.get('search', '')
        print(search)
        categories = Category.objects.filter(name__icontains=str(search)).order_by('id')
        results = []
        for category in categories:
            results.append({
                'id': category.id,
                'name': category.name
            })
        data_json = json.dumps(results)
        mimetype = "application/json"
        return HttpResponse(data_json, mimetype)

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def recalculate_product(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe el producto.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        products = Product.objects.all()

        for product in products:

            batches = Batch.objects.filter(product_id=product.pk)

            if batches.count() > 0:

                print('product.pk: ', product.pk)
                sum_batches = batches.aggregate(Sum('total_quantity'))
                sum_details = 0

                for batch in batches.all():
                    detail = BatchDetail.objects.filter(batch_id=batch.id, type='C')
                    sum_details += detail[0].quantity

                purchased_inventory = sum_details
                if sum_batches is not None:
                    current_inventory = int(sum_batches['total_quantity__sum'])
                else:
                    current_inventory = 0
                returned_purchased_inventory = 0
                returned_sold_inventory = 0
                sold_inventory = purchased_inventory - current_inventory

                # print 'Comprado: ', purchased_inventory
                # print 'Vendido: ', sold_inventory
                # print 'A la mano: ', current_inventory

                product.purchased_inventory = purchased_inventory
                product.current_inventory = current_inventory
                product.sold_inventory = sold_inventory
                product.returned_purchased_inventory = returned_purchased_inventory
                product.returned_sold_inventory = returned_sold_inventory
                product.save()

        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'info': True, 'title': 'Atento',
               'message': 'Verifique, antes de almacenar las modificaciones hechas a los datos.'})
        return JsonResponse({
            'success': True,
            'alert': t2.render(c2)
        })

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def generate_purchase_receipt(request):
    if request.method == 'GET':
        receipt_request = request.GET.get('receipt', '')
        data = json.loads(receipt_request)

        branch_office_id = str(data['BranchOffice'])
        supplier_id = str(data['Supplier'])
        print('branch_office_id: ', branch_office_id)
        branch_office = BranchOffice.objects.get(id=int(branch_office_id))
        supplier = Supplier.objects.get(id=int(supplier_id))
        employee = Employee.objects.get(user=request.user)
        request_date = parse_date(data['RequestDate'])

        if request_date is None:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'La fecha de la compra esta vacia.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        data_purchase = {
            'supplier': supplier,
            'employee': employee,
            'type': 'F',
            'subtotal': float(data['Subtotal']),
            # 'igv': float(data['Igv']),
            'total': float(data['Total']),
            'operation_number': str(data['OperationNumber']),
            'request_date': request_date,
            'branch_office': branch_office
            # 'observation': observation,
        }
        purchase = Purchase.objects.create(**data_purchase)
        purchase.save()

        for a in data['Details']:
            product = Product.objects.get(id=int(a['Product']))

            count_editions = Batch.objects.filter(product_id__exact=int(a['Product'])).count()

            if int(a['Quantity']) > 0:

                data_acquisition_detail = {
                    'rate': float(a['Price']),
                    'quantity_ordered': int(a['Quantity']),
                    'amount': float(a['Rode']),
                    'product': product,
                    'purchase': purchase
                }
                acquisition_detail = AcquisitionDetail.objects.create(**data_acquisition_detail)
                # acquisition_detail = AcquisitionDetail.objects.filter(product_return__isnull=)
                acquisition_detail.save()

                data_batch = {
                    'product': product,
                    'barcode': '000',
                    'edition': count_editions + 1,
                    'total_quantity': int(a['Quantity']),
                    'entry_date': request_date
                }
                batch = Batch.objects.create(**data_batch)
                batch.save()

                batch_id = batch.edition

                barcode = product.barcode

                code = '000'

                if batch_id < 1000:
                    if batch_id < 100:
                        if batch_id < 10:
                            code = barcode, '00', str(batch_id)
                        else:
                            code = barcode, '0', str(batch_id)
                    else:
                        code = barcode, str(batch_id)
                else:
                    t = loader.get_template('vetstore/alerts.html')
                    c = ({'danger': True, 'title': '¡Error!', 'message': 'excedio el numero de lotes.'})
                    return JsonResponse({'success': False, 'alert': t.render(c)})

                code = "".join(code)

                batch.barcode = code
                batch.save()

                # crear detalle lote
                data_batch_detail = {
                    'batch': batch,
                    'type': 'C',
                    'entry_date': request_date,
                    'quantity': int(a['Quantity']),
                    'acquisition_detail': acquisition_detail
                }
                batch_detail = BatchDetail.objects.create(**data_batch_detail)
                batch_detail.save()

                product.purchased_inventory += int(a['Quantity'])
                product.current_inventory += int(a['Quantity'])
                product.save()

                if product.current_inventory <= product.minimum_inventory:
                    product.status = 'S'
                    product.save()
                else:
                    if product.current_inventory > product.minimum_inventory:
                        product.status = 'A'
                        product.save()
        now = datetime.now()
        purchases = Purchase.objects.filter(created_at__year=now.year, created_at__month=now.month,
                                            created_at__day=now.day).order_by('-created_at')

        t = loader.get_template('vetstore/purchase-list.html')
        c = ({'purchases': purchases})

        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'success': True, 'title': '¡Bien hecho!',
               'message': 'El recibo se ha generado correctamente.'})
        return JsonResponse({'success': True, 'message': 'Encontrado!', 'list': t.render(c), 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def purchase_product_autocomplete_list(request):
    if request.is_ajax():
        search = request.GET.get('search', '')
        products = Product.objects.filter(Q(name__icontains=str(search)) | Q(
            barcode__icontains=str(search)) | Q(factory_barcode__icontains=str(search))).order_by('id')
        results = []
        for product in products:
            results.append({
                'id': product.id,
                'name': product.name,
                'barcode': product.barcode,
                'factory_barcode': product.factory_barcode,
                'sale_price': str(product.sale_price),
                'pass_price': str(product.pass_price),
                'discount_price': str(product.discount_price),
                'current_inventory': str(product.current_inventory),
            })
        data_json = json.dumps(results)
        mimetype = "application/json"
        return HttpResponse(data_json, mimetype)
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def sale_product_autocomplete_list(request):
    if request.is_ajax():
        search = request.GET.get('search', '')
        print(search)
        batches = Batch.objects.filter(
            barcode__icontains=str(search)).order_by('entry_date')
        results = []
        for batch in batches:
            sales = [(
                s.acquisition_detail.sales.pk,
                str(s.acquisition_detail.sales.sale_date),
                str(s.acquisition_detail.rate),
                s.quantity,
                str(s.subtotal),
                str(s.acquisition_detail.sales.created_at)
            ) for s in BatchDetail.objects.filter(type='V').filter(batch__barcode__icontains=str(search)).order_by('-id')]

            purchases = [(
                p.acquisition_detail.purchase.pk,
                str(p.acquisition_detail.purchase.request_date),
                str(p.acquisition_detail.rate),
                p.quantity,
                str(p.subtotal)
            ) for p in BatchDetail.objects.filter(type='C').filter(batch__barcode__icontains=str(search)).order_by('-id')]

            results.append({
                'id': batch.product.id,
                'name': batch.product.name,
                'barcode': batch.product.barcode,
                'factory_barcode': batch.product.factory_barcode,
                'sale_price': str(batch.product.sale_price),
                'pass_price': str(batch.product.pass_price),
                'discount_price': str(batch.product.discount_price),
                'current_inventory': str(batch.product.current_inventory),
                'batch_barcode': batch.barcode,
                'batch_total_quantity': batch.total_quantity,
                'sales': sales,
                'purchases': purchases,
                'wholesales': [{
                    'id': w.pk,
                    'quantity': w.quantity,
                    'price': str(w.price)
                } for w in Wholesale.objects.filter(product_id=batch.product.id)]
            })
        data_json = json.dumps(results)
        mimetype = "application/json"
        return HttpResponse(data_json, mimetype)
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def product_return_product_autocomplete_list(request):
    if request.is_ajax():
        search = request.GET.get('search', '')
        batches = Batch.objects.filter(
            barcode__icontains=str(search)).order_by('entry_date')
        results = []
        for batch in batches:
            sales = []
            sales_batches = BatchDetail.objects.filter(type='V').filter(
                batch__barcode__icontains=str(search)).order_by('-id')

            for s in sales_batches:
                if s.acquisition_detail.sales.status == 'A':
                    sales.append((
                        s.acquisition_detail.sales.pk,
                        str(s.acquisition_detail.sales.sale_date),
                        str(s.acquisition_detail.rate),
                        s.quantity,
                        str(s.subtotal),
                        str(s.acquisition_detail.sales.created_at)
                    ))

            purchases = []
            purchases_batches = BatchDetail.objects.filter(type='C').filter(
                batch__barcode__icontains=str(search)).order_by('-id')

            for p in purchases_batches:
                purchases.append((
                    p.acquisition_detail.purchase.pk,
                    str(p.acquisition_detail.purchase.request_date),
                    str(p.acquisition_detail.rate),
                    p.quantity,
                    str(p.subtotal)
                ))

            results.append({
                'id': batch.product.id,
                'name': batch.product.name,
                'barcode': batch.product.barcode,
                'factory_barcode': batch.product.factory_barcode,
                'sale_price': str(batch.product.sale_price),
                'pass_price': str(batch.product.pass_price),
                'discount_price': str(batch.product.discount_price),
                'current_inventory': str(batch.product.current_inventory),
                'batch_barcode': batch.barcode,
                'batch_total_quantity': batch.total_quantity,
                'sales': sales,
                'purchases': purchases,
                'wholesales': [{
                    'id': w.pk,
                    'quantity': w.quantity,
                    'price': str(w.price)
                } for w in Wholesale.objects.filter(product_id=batch.product.id)]
            })
        data_json = json.dumps(results)
        mimetype = "application/json"
        return HttpResponse(data_json, mimetype)

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def supplier_list(request):
    if request.is_ajax():
        search = request.GET.get('search', '')
        print(search)
        suppliers = Supplier.objects.filter(name__icontains=str(search)).order_by('id')

        results = []
        for supplier in suppliers:
            results.append({
                'id': supplier.id,
                'name': supplier.name
            })
        data_json = json.dumps(results)
        mimetype = "application/json"
        return HttpResponse(data_json, mimetype)

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def way_pay(request):
    if request.method == 'GET':
        choices = Sales._meta.get_field('way_pay').choices
        results = []
        for id, value in choices:
            results.append({
                'id': id,
                'value': value
            })
        data_json = json.dumps(results)
    mimetype = "application/json"
    return HttpResponse(data_json, mimetype)


def product_return_type(request):
    if request.method == 'GET':
        choices = ProductReturn._meta.get_field('type').choices
        results = []
        for id, value in choices:
            results.append({
                'id': id,
                'value': value
            })
        data_json = json.dumps(results)
    mimetype = "application/json"
    return HttpResponse(data_json, mimetype)


@csrf_exempt
def generate_sales_receipt(request):
    if request.method == 'GET':
        receipt_request = request.GET.get('receipt', '')
        data = json.loads(receipt_request)

        customer_id = str(data['CustomerId'])
        customer = Customer.objects.get(pk=int(customer_id))

        # branch_office_id = str(data['BranchOffice'])
        # branch_office = BranchOffice.objects.get(id=int(branch_office_id))
        connected_employee = Employee.objects.get(user=request.user)
        branch_office_connected_employee = connected_employee.branch_office

        code_id = str(data['EmployeeCode'])

        request_date = parse_date(data['RequestDate'])

        try:
            employee = Employee.objects.get(code__exact=int(code_id))
        except Employee.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe el empleado.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        # way_pay = str(data['WayPay'])

        if data['Charged'] is None:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'Nada por cobrar.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        if float(data['Received']) == 0:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'Ingresar monto recibido.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        data_sales = {
            'customer': customer,
            'employee': employee,
            'branch_office': branch_office_connected_employee,
            # 'way_pay': way_pay,
            'charged': float(data['Charged']),
            'received': float(data['Received']),
            'turned': float(data['Turned']),
            'sale_date': request_date,
            # 'observation': observation,
        }
        print(data_sales)
        sales = Sales.objects.create(**data_sales)
        sales.save()

        for a in data['Details']:
            product = Product.objects.get(id=int(a['Product']))

            if int(a['Quantity']) > 0 and int(a['Quantity']) <= product.current_inventory:
                data_acquisition_detail = {
                    'rate_estimated': product.sale_price,
                    'rate': float(a['Price']),
                    'quantity_ordered': int(a['Quantity']),
                    'amount': float(a['Rode']),
                    'product': product,
                    'sales': sales
                }
                acquisition_detail = AcquisitionDetail.objects.create(**data_acquisition_detail)
                acquisition_detail.save()

                formatted_time = date.today()

                for b in a['Batches']:
                    batch = Batch.objects.get(barcode__exact=str(b['BatchBarcode']))
                    quantity = int(b['BatchQuantity'])

                    if batch.total_quantity >= quantity:

                        data_batch_detail = {
                            'batch': batch,
                            'type': 'V',
                            'quantity': quantity,
                            'entry_date': formatted_time,
                            'acquisition_detail': acquisition_detail
                        }
                        batch_detail = BatchDetail.objects.create(**data_batch_detail)
                        batch_detail.save()

                        batch.total_quantity = batch.total_quantity - quantity
                        batch.save()

                product.sold_inventory += int(a['Quantity'])
                product.current_inventory -= int(a['Quantity'])
                product.save()

                if product.current_inventory <= product.minimum_inventory:
                    product.status = 'S'
                    product.save()
                else:
                    if product.current_inventory > product.minimum_inventory:
                        product.status = 'A'
                        product.save()
            else:
                t = loader.get_template('vetstore/alerts.html')
                c = ({'danger': True, 'title': '¡Error!',
                      'message': 'No existe suficiente stock para '.join(product.name)})
                return JsonResponse({'success': False, 'alert': t.render(c)})

        for w in data['WayPay']:
            way_pay = WayPay.objects.get(id=int(w['Way']))

            if way_pay is not None:
                data_payment_method = {
                    'rode': float(w['Rode']),
                    'way_pay': way_pay,
                    'sales': sales
                }
                payment_method = RegistrationPaymentMethod.objects.create(**data_payment_method)
                print('w[ProductReturnId]: ', w['ProductReturnId'])
                if int(w['ProductReturnId']) > 0:
                    pr = ProductReturn.objects.get(id=int(w['ProductReturnId']))
                    payment_method.product_return = pr
                    pr.status = 'I'
                    pr.save()
                payment_method.save()

        now = datetime.now()
        sales = Sales.objects.filter(created_at__date__year=now.year, created_at__date__month=now.month,
                                     created_at__date__day=now.day).order_by('-created_at')

        sales_gain_obtained_sum = 0
        sales_gain_estimated_sum = 0
        sales_total_discount_turned_sum = 0

        for sale in sales:
            for detail in sale.detail_sales.all():
                sales_gain_obtained_sum += detail.profit_per_product_in_sales_obtained
                sales_gain_estimated_sum += detail.profit_per_product_in_sales_estimated
                sales_total_discount_turned_sum += detail.discount_per_product_in_sales
        charged_sum = sales.aggregate(Sum('charged'))
        received_sum = sales.aggregate(Sum('received'))
        turned_sum = sales.aggregate(Sum('turned'))

        role = connected_employee.role.first().code

        t = loader.get_template('vetstore/sales-list.html')
        c = ({
            'role': role,
            'sales': sales,
            'charged_sum': charged_sum,
            'received_sum': received_sum,
            'turned_sum': turned_sum,
            'sales_gain_obtained_sum': sales_gain_obtained_sum,
            'sales_gain_estimated_sum': sales_gain_estimated_sum,
            'sales_total_discount_turned_sum': sales_total_discount_turned_sum
        })

        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'success': True, 'title': '¡Bien hecho!',
               'message': 'El recibo se ha generado correctamente.'})
        return JsonResponse({'success': True, 'message': 'Encontrado!', 'list': t.render(c), 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    writer.writerow(['Username', 'First name', 'Last name', 'Email address'])

    users = User.objects.all().values_list('username', 'first_name', 'last_name', 'email')
    for user in users:
        writer.writerow(user)

    return response


def export_products_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="productos.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Creado',
        'Modificado',
        'Nombre',
        'Categoria',
        'Marca',
        'Precio de venta',
        'Precio de pase',
        'Precio de rebaja',
        'Inventario comprado',
        'Inventario vendido',
        'Inventario comprado devuelto',
        'Inventario vendido devuelto',
        'Inventario a la mano',
        'Inventario mínimo',
        'Estado',
    ])
    products = [(
        p.create_at,
        p.update_at,
        p.name,
        p.category.name,
        p.brand.name,
        p.sale_price,
        p.pass_price,
        p.discount_price,
        p.purchased_inventory,
        p.sold_inventory,
        p.returned_purchased_inventory,
        p.returned_sold_inventory,
        p.current_inventory,
        p.minimum_inventory,
        p.get_status_display(),
    ) for p in Product.objects.all()]

    for detail in products:
        writer.writerow(detail)

    return response


def export_batches_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="lotes.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Id compra',
        'Comprobante',
        'Fecha de compra',
        'Nombre',
        'barcode Lote',
        'Edision Lote',
        'Precio de compra',
        'Cantidad total comprada',
        'Precio total compra',
        'Stock actual',
        'Precio de stock sobrante',
        'Precio de venta',
        'Ganancia de stock sobrante',
        'Sucursal',
        'Categoria',
    ])
    details = [(
        d.acquisition_detail.purchase.pk,
        d.acquisition_detail.purchase.operation_number,
        d.acquisition_detail.purchase.request_date,
        d.batch.product.name,
        d.batch.barcode,
        d.batch.edition,
        d.acquisition_detail.rate,
        d.acquisition_detail.quantity_ordered,
        d.acquisition_detail.amount,
        d.batch.total_quantity,
        d.excess_stock_price,
        d.batch.product.sale_price,
        d.remaining_stock_gain,
        d.acquisition_detail.purchase.employee.branch_office.name,
        d.batch.product.category.name
    ) for d in BatchDetail.objects.filter(type='C')]

    # details = BatchDetail.objects.filter(type='C').values_list(
    #     'acquisition_detail__purchase__operation_number',
    #     'batch__product__name',
    #     'batch__barcode',
    #     'acquisition_detail__rate',
    #     'acquisition_detail__quantity_ordered',
    #     'acquisition_detail__amount',
    #     'batch__total_quantity',
    #     'profit_obtained()'
    # )
    for detail in details:
        writer.writerow(detail)

    return response


@csrf_exempt
def supplier_registration(request):
    if request.method == 'POST':

        name = str(request.POST.get('name', ''))

        if name:
            try:
                supplier = Supplier.objects.get(name__exact=name)
                t = loader.get_template('vetstore/alerts.html')
                c = ({'danger': True, 'title': '¡Error!', 'message': 'Nombre de proveedor duplicado.'})
                return JsonResponse({'success': False, 'alert': t.render(c)})
            except Supplier.DoesNotExist:
                data = {
                    'name': name,
                    'cellphone': request.POST.get('cellphone', ''),
                    'contact': request.POST.get('contact', '')
                }
                supplier = Supplier.objects.create(**data)
                supplier.save()
        else:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'Nombre vacio.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        suppliers = Supplier.objects.all()

        t3 = loader.get_template('vetstore/supplier-list.html')
        c3 = ({'suppliers': suppliers})

        t = loader.get_template('vetstore/alerts.html')
        c = ({'success': True, 'title': '¡Bien hecho!',
              'message': 'Los datos se han registrado correctamente.'})
        return JsonResponse({'success': True, 'alert': t.render(c), 'list': t3.render(c3)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def supplier_update(request):
    if request.method == 'POST':
        id = request.POST.get('supplier-id', 0)

        try:
            supplier = Supplier.objects.get(pk=int(id))
        except Supplier.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No existe el proveedor.'})

        supplier.name = str(request.POST.get('name', ''))
        supplier.cellphone = str(request.POST.get('cellphone', ''))
        supplier.contact = str(request.POST.get('contact', ''))

        supplier.save()

        suppliers = Supplier.objects.all()

        t3 = loader.get_template('vetstore/supplier-list.html')
        c3 = ({'suppliers': suppliers})

        t = loader.get_template('vetstore/alerts.html')
        c = ({'success': True, 'title': '¡Bien hecho!',
              'message': 'Los datos se han actualizado correctamente.'})
        return JsonResponse({'success': True, 'alert': t.render(c), 'list': t3.render(c3)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def get_supplier(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            supplier = Supplier.objects.get(id=pk)
        except Supplier.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe el proveedor.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        t = loader.get_template('vetstore/supplier-update-form.html')
        c = ({'supplier': supplier})
        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'info': True, 'title': 'Atento',
               'message': 'Verifique, antes de almacenar las modificaciones hechas a los datos.'})
        return JsonResponse({
            'success': True,
            'formupdate': t.render(c),
            'alert': t2.render(c2)
        })

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def attendance_registration(request):
    if request.method == 'POST':

        code = request.POST.get('employee-code', '')
        created_at = request.POST.get('created_at', '')

        # parsed = parse_datetime('2001-12-11T09:27:24.895551')
        # parsed = parse_datetime(created_at)
        parsed = datetime.now()
        print('parsed: ', parsed)

        try:
            employee = Employee.objects.get(code__exact=int(code))
        except Employee.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe empleado.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})
        schedule = employee.schedule
        tolerance = schedule.tolerance

        # busco dia actual
        durations = schedule.durations.filter(day_week__exact=switch_day(parsed.weekday()))
        duration = durations.first()

        if duration is None:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'Dia no registrado.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})
        else:
            start_working_day = duration.start_working_day
            end_working_day = duration.end_working_day
            start_time = duration.start_time
            end_time = duration.end_time

        status = 'N'
        minutes_late = 0
        minutes_early = 0
        minutes_delay = 0
        minutes_extra = 0
        hours_worked = 0

        attendance = Attendance.objects.filter(employee__user_id=employee.user.pk).filter(
            date_assigned__year=parsed.year, date_assigned__month=parsed.month, date_assigned__day=parsed.day)
        registered_assist = attendance.count()
        print('registered_assist: ', registered_assist)

        if registered_assist == 0:

            e0 = datetime(parsed.year, parsed.month, parsed.day)  # 00:00:00
            e1 = e0 + timedelta(hours=start_working_day.hour) - timedelta(seconds=1)  # 08:59:59
            e2 = e1 + timedelta(seconds=1)  # 09:00:00
            e3 = e1 + timedelta(minutes=tolerance)  # 09:05:59
            e4 = e3 + timedelta(seconds=1)  # 09:06:00
            e5 = e0 + timedelta(hours=end_time.hour) + timedelta(minutes=end_time.minute) + \
                timedelta(seconds=end_time.second)  # 23:59:59

            if parsed >= e0 and parsed <= e1:  # 00:00:00 - 08:59:59
                status = 'E'
                diff = e2 - parsed
                minutes_early = (diff.days * 1440 + diff.seconds / 60)
                print('minutes_early: ', minutes_early)
            else:
                if parsed >= e2 and parsed <= e3:  # 09:00:00 - 09:05:59
                    status = 'O'
                else:
                    if parsed >= e4 and parsed <= e5:  # 09:06:00 - 23:59:59
                        status = 'L'
                        diff = parsed - e4
                        minutes_late = (diff.days * 1440 + diff.seconds / 60)
                        print('minutes_late: ', minutes_late)
            data_attendance = {
                'employee': employee,
                'type': 'A',
                'date_assigned': parsed.date(),
                'entry_time': parsed.time(),
                'minutes_late': minutes_late,
                'minutes_early': minutes_early,
            }
            new_attendance = Attendance.objects.create(**data_attendance)
            new_attendance.save()

            data_attendance_detail = {
                'attendance': new_attendance,
                'status': status,
                'registered_time': parsed.time()
            }
            attendance_detail = AttendanceDetail.objects.create(**data_attendance_detail)
            attendance_detail.save()
            print('Entrada')
        else:
            if registered_assist == 1:

                s0 = datetime(parsed.year, parsed.month, parsed.day)  # 00:00:00
                s1 = s0 + timedelta(hours=end_working_day.hour) - timedelta(seconds=1)  # 20:59:59
                s2 = s0 + timedelta(hours=end_working_day.hour)  # 21:00:00
                s3 = s2 + timedelta(seconds=59)  # 21:00:59
                s4 = s3 + timedelta(seconds=1)  # 21:01:00
                s5 = s0 + timedelta(hours=end_time.hour) + timedelta(minutes=end_time.minute) + \
                    timedelta(seconds=end_time.second)  # 23:59:59

                if parsed >= s0 and parsed <= s1:  # 00:00:00 - 20:59:59
                    status = 'E'
                    diff = s2 - parsed
                    minutes_delay = (diff.days * 1440 + diff.seconds / 60)
                    print('minutes_delay: ', minutes_delay)
                else:
                    if parsed >= s2 and parsed <= s3:  # 21:00:00 - 21:00:59
                        status = 'O'
                    else:
                        if parsed > s4 and parsed <= s5:  # 21:01:00 - 23:59:59
                            status = 'L'
                            diff = parsed - s2
                            minutes_extra = (diff.days * 1440 + diff.seconds / 60)
                            print('minutes_extra: ', minutes_extra)
                assistance = attendance.first()

                if assistance.departure_time is not None:
                    t = loader.get_template('vetstore/alerts.html')
                    c = ({'warning': True, 'title': '¡Atencion!',
                          'message': 'Ya registro entrada y salida.'})
                    return JsonResponse({'success': False, 'alert': t.render(c)})
                else:

                    # Definir hora de entrada y salida
                    entry_date_time = s0 + timedelta(hours=assistance.entry_time.hour) + timedelta(
                        minutes=assistance.entry_time.minute) + timedelta(seconds=assistance.entry_time.second)
                    departure_time = parsed

                    # Calcular horas trabajadas
                    hours_worked = departure_time - entry_date_time
                    duration_in_s = hours_worked.total_seconds()
                    temp = s0 + timedelta(seconds=duration_in_s)
                    # attendance = Attendance.objects.create(**data_attendance)

                    assistance.departure_time = departure_time.time()
                    assistance.save()
                    assistance.hours_worked = temp.time()
                    assistance.save()
                    assistance.minutes_delay = minutes_delay
                    assistance.save()
                    assistance.minutes_extra = minutes_extra
                    assistance.save()

                    data_attendance_detail = {
                        'attendance': assistance,
                        'status': status,
                        'registered_time': departure_time.time()
                    }
                    print(data_attendance_detail)

                    attendance_detail = AttendanceDetail.objects.create(**data_attendance_detail)
                    attendance_detail.save()

                    print('Salida')
            else:
                print('No registrar nada')

        now = datetime.now()
        # attendances = Attendance.objects.all().order_by('-date_assigned')
        attendances = Attendance.objects.filter(date_assigned__year=now.year, date_assigned__month=now.month,
                                                date_assigned__day=now.day).order_by('-date_assigned')

        t3 = loader.get_template('vetstore/attendance-list.html')
        c3 = ({'attendances': attendances})

        t = loader.get_template('vetstore/alerts.html')
        c = ({'success': True, 'title': '¡Bien hecho!',
              'message': 'Los datos se han registrado correctamente.'})
        return JsonResponse({'success': True, 'alert': t.render(c), 'list': t3.render(c3)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def switch_day(argument):
    switcher = {
        0: "Lu",
        1: "Ma",
        2: "Mi",
        3: "Ju",
        4: "Vi",
        5: "Sa",
        6: "Do"
    }
    return switcher.get(argument, 7)


def get_attendances_list(request):
    if request.method == 'GET':

        start = parse_date(request.GET.get('start-date', ''))
        final = parse_date(request.GET.get('end-date', ''))
        mode = str(request.GET.get('mode', ''))
        employee_id = int(request.GET.get('employee-id', 0))

        print('employee_id: ', employee_id)

        if start is None:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'La fecha inicial esta vacia.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})
        else:
            hours_worked_sum = 0
            minutes_late_sum = 0
            minutes_early_sum = 0
            minutes_delay_sum = 0
            minutes_extra_sum = 0

            attendances = []

            if mode == 'EQUALS':
                print('EQUALS: ')

                last = start + timedelta(days=1)
                first = start - timedelta(days=1)
                # first = start
                print('first: ', first)
                print('last: ', last)
                if employee_id == 0:
                    attendances = Attendance.objects.filter(
                        date_assigned__gt=first, date_assigned__lt=last).order_by('date_assigned')
                else:
                    attendances = Attendance.objects.filter(employee__user_id=employee_id).filter(
                        date_assigned__gt=first, date_assigned__lt=last).order_by('date_assigned')

                hours_worked_sum = attendances.aggregate(Sum('hours_worked'))
                minutes_late_sum = attendances.aggregate(Sum('minutes_late'))
                minutes_early_sum = attendances.aggregate(Sum('minutes_early'))
                minutes_delay_sum = attendances.aggregate(Sum('minutes_delay'))
                minutes_extra_sum = attendances.aggregate(Sum('minutes_extra'))

            else:
                if mode == 'GREATER_THAN':
                    print('GREATER_THAN: ')
                    first = start
                    print(first)
                    if employee_id == 0:
                        attendances = Attendance.objects.filter(
                            date_assigned__gt=first).order_by('date_assigned')
                    else:
                        attendances = Attendance.objects.filter(employee__user_id=employee_id).filter(
                            date_assigned__gt=first).order_by('date_assigned')

                    hours_worked_sum = attendances.aggregate(Sum('hours_worked'))
                    minutes_late_sum = attendances.aggregate(Sum('minutes_late'))
                    minutes_early_sum = attendances.aggregate(Sum('minutes_early'))
                    minutes_delay_sum = attendances.aggregate(Sum('minutes_delay'))
                    minutes_extra_sum = attendances.aggregate(Sum('minutes_extra'))
                else:
                    if mode == 'LESS_THAN':
                        print('LESS_THAN: ')
                        if employee_id == 0:
                            attendances = Attendance.objects.filter(
                                date_assigned__lt=start).order_by('date_assigned')
                        else:
                            attendances = Attendance.objects.filter(employee__user_id=employee_id).filter(
                                date_assigned__lt=start).order_by('date_assigned')

                        hours_worked_sum = attendances.aggregate(Sum('hours_worked'))
                        minutes_late_sum = attendances.aggregate(Sum('minutes_late'))
                        minutes_early_sum = attendances.aggregate(Sum('minutes_early'))
                        minutes_delay_sum = attendances.aggregate(Sum('minutes_delay'))
                        minutes_extra_sum = attendances.aggregate(Sum('minutes_extra'))

                    else:
                        if mode == 'BETWEEN':
                            print('BETWEEN: ')
                            if final is None:
                                t = loader.get_template('vetstore/alerts.html')
                                c = ({'danger': True, 'title': '¡Error!',
                                      'message': 'La fecha final esta vacia.'})
                                return JsonResponse({'success': False, 'alert': t.render(c)})
                            else:
                                if final < start:
                                    t = loader.get_template('vetstore/alerts.html')
                                    c = ({'danger': True, 'title': '¡Error!',
                                          'message': 'La fecha final es menor a la inicial.'})
                                    return JsonResponse({'success': False, 'alert': t.render(c)})
                                else:
                                    if final == start:
                                        t = loader.get_template('vetstore/alerts.html')
                                        c = ({'danger': True, 'title': '¡Error!',
                                              'message': 'La fecha final es igual a la inicial.'})
                                        return JsonResponse({'success': False, 'alert': t.render(c)})
                                print('final: ', final)
                                print('start: ', start)
                                # first = start + timedelta(days=1)
                                last = final + timedelta(days=1)
                                if employee_id == 0:
                                    attendances = Attendance.objects.filter(date_assigned__gte=start).filter(
                                        date_assigned__lt=last).order_by('date_assigned')
                                else:
                                    attendances = Attendance.objects.filter(employee__user_id=employee_id).filter(
                                        date_assigned__gte=start).filter(date_assigned__lt=last).order_by('date_assigned')

                                hours_worked_sum = attendances.aggregate(Sum('hours_worked'))
                                minutes_late_sum = attendances.aggregate(Sum('minutes_late'))
                                minutes_early_sum = attendances.aggregate(Sum('minutes_early'))
                                minutes_delay_sum = attendances.aggregate(Sum('minutes_delay'))
                                minutes_extra_sum = attendances.aggregate(Sum('minutes_extra'))

            if not attendances:
                t = loader.get_template('vetstore/alerts.html')
                c = ({'warning': True, 'title': '¡Atención!', 'message': 'Registros no encontrados.'})
                return JsonResponse({'success': False, 'alert': t.render(c)})
            employee = Employee.objects.get(user=request.user)
            role = employee.role.first().code
            print('role: ', role)
            t = loader.get_template('vetstore/attendance-list.html')
            c = ({
                'role': role,
                'attendances': attendances,
                'hours_worked_sum': hours_worked_sum,
                'minutes_late_sum': minutes_late_sum,
                'minutes_early_sum': minutes_early_sum,
                'minutes_delay_sum': minutes_delay_sum,
                'minutes_extra_sum': minutes_extra_sum,

            })

            t2 = loader.get_template('vetstore/alerts.html')
            c2 = ({'success': True, 'title': '¡Bien hecho!', 'message': 'Busqueda exitosa.'})

            return JsonResponse({'success': True, 'list': t.render(c), 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def expense_registration(request):
    if request.method == 'POST':

        code = request.POST.get('employee-code', '')

        try:
            employee = Employee.objects.get(code__exact=int(code))
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No existe empleado.'})

        connected_employee = Employee.objects.get(user=request.user)
        branch_office_connected_employee = connected_employee.branch_office

        data = {
            'employee': employee,
            'description': request.POST.get('description', ''),
            'rode': float(request.POST.get('rode', 0)),
            'expense_date': parse_date(request.POST.get('expense-date', '')),
            'branch_office': branch_office_connected_employee,
        }
        expense = Expense.objects.create(**data)
        expense.save()

        expenses = Expense.objects.all()

        t3 = loader.get_template('vetstore/expense-list.html')
        c3 = ({'expenses': expenses})

        t = loader.get_template('vetstore/alerts.html')
        c = ({'success': True, 'title': '¡Bien hecho!',
              'message': 'Los datos se han registrado correctamente.'})
        return JsonResponse({'success': True, 'alert': t.render(c), 'list': t3.render(c3)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def generate_product_return_receipt(request):
    if request.method == 'GET':
        receipt_request = request.GET.get('receipt', '')
        data = json.loads(receipt_request)

        code_id = str(data['EmployeeCode'])
        comment = str(data['Comment'])
        return_date = parse_date(data['ReturnDate'])
        type = str(data['Type'])

        try:
            employee = Employee.objects.get(code__exact=int(code_id))
        except Employee.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe el empleado.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        connected_employee = Employee.objects.get(user=request.user)
        branch_office_connected_employee = connected_employee.branch_office

        data_product_return = {
            'employee': employee,
            'type': type,
            'comment': comment,
            'return_date': return_date
        }
        product_return = ProductReturn.objects.create(**data_product_return)
        product_return.save()

        quantity_shipped = 0
        sale_id = 0
        purchase_id = 0

        formatted_time = date.today()

        if type == 'V':

            old_sale_id = int(data['SaleId'])
            old_sale = Sales.objects.get(id=old_sale_id)
            old_sale.status = 'C'
            old_sale.save()

            acquisitions_remaining = []

            for acquisition in old_sale.detail_sales.all():

                batch_acquisition = Batch.objects.get(
                    barcode__exact=acquisition.acquisitions.first().batch.barcode)
                data_batch_detail = {
                    'batch': batch_acquisition,
                    'type': 'R',
                    'quantity': acquisition.quantity_ordered,
                    'entry_date': formatted_time,
                    'acquisition_detail': acquisition
                }
                batch_detail = BatchDetail.objects.create(**data_batch_detail)
                batch_detail.save()

                product = acquisition.product
                product.returned_sold_inventory = product.returned_sold_inventory + acquisition.quantity_ordered
                product.current_inventory = product.current_inventory + acquisition.quantity_ordered
                product.save()

                batch_acquisition.total_quantity = batch_acquisition.total_quantity + acquisition.quantity_ordered
                batch_acquisition.save()

                for detail in data['Details']:

                    if acquisition.product_id == int(detail['Product']):
                        quantity_remaining = acquisition.quantity_ordered - int(detail['Quantity'])
                        if quantity_remaining > 0:

                            acquisitions_remaining.append({
                                'rate_estimated': acquisition.rate_estimated,
                                'rate': acquisition.rate,
                                'quantity_ordered': quantity_remaining,
                                'amount': acquisition.rate * quantity_remaining,
                                'product': acquisition.product,
                                'batch': batch_acquisition
                            })
                    else:
                        acquisitions_remaining.append({
                            'rate_estimated': acquisition.rate_estimated,
                            'rate': acquisition.rate,
                            'quantity_ordered': acquisition.quantity_ordered,
                            'amount': acquisition.amount,
                            'product': acquisition.product,
                            'batch': batch_acquisition
                        })

            if len(acquisitions_remaining) > 0:

                data_new_sale = {
                    'customer': old_sale.customer,
                    'employee': employee,
                    'branch_office': branch_office_connected_employee,
                    'way_pay': old_sale.way_pay,
                    'sale_date': return_date,
                    # 'observation': observation,
                }
                new_sale = Sales.objects.create(**data_new_sale)
                new_sale.save()

                charged = 0

                for detail in acquisitions_remaining:
                    data_acquisition_detail = {
                        'rate_estimated': detail['rate_estimated'],
                        'rate': float(detail['rate']),
                        'quantity_ordered': int(detail['quantity_ordered']),
                        'amount': float(detail['amount']),
                        'product': detail['product'],
                        'sales': new_sale
                    }
                    charged += float(detail['rate']) * int(detail['quantity_ordered'])
                    acquisition_detail = AcquisitionDetail.objects.create(**data_acquisition_detail)
                    acquisition_detail.save()

                    data_batch_detail = {
                        'batch': detail['batch'],
                        'type': 'V',
                        'quantity': int(detail['quantity_ordered']),
                        'entry_date': formatted_time,
                        'acquisition_detail': acquisition_detail
                    }
                    batch_detail = BatchDetail.objects.create(**data_batch_detail)
                    batch_detail.save()

                    product = detail['product']
                    product.sold_inventory = product.sold_inventory + \
                        int(detail['quantity_ordered'])
                    product.current_inventory = product.current_inventory - \
                        int(detail['quantity_ordered'])
                    product.save()

                    batch_new_acquisition = detail['batch']
                    batch_new_acquisition.total_quantity = batch_new_acquisition.total_quantity - \
                        int(detail['quantity_ordered'])
                    batch_new_acquisition.save()

                    if product.current_inventory <= product.minimum_inventory:
                        product.status = 'S'
                        product.save()
                    else:
                        if product.current_inventory > product.minimum_inventory:
                            product.status = 'A'
                            product.save()

                new_sale.charged = charged
                new_sale.received = charged
                new_sale.save()

            product_return.sales = old_sale
        else:
            if type == 'C':
                purchase_id = int(data['PurchaseId'])
                purchase = Purchase.objects.get(id=purchase_id)
                product_return.purchase = purchase
        product_return.save()

        for a in data['Details']:
            product = Product.objects.get(id=int(a['Product']))
            quantity_shipped += int(a['Quantity'])
            data_acquisition_detail = {
                'rate_estimated': float(a['Rate']),
                'rate': float(a['Rate']),
                'quantity_received': int(a['Quantity']),
                'amount': float(a['Amount']),
                'product': product,
                'product_return': product_return,
            }
            acquisition_detail = AcquisitionDetail.objects.create(**data_acquisition_detail)
            acquisition_detail.save()

            batch = Batch.objects.get(barcode__exact=str(a['BatchBarcode']))

            if type == 'V':
                acquisition_detail.sales = Sales.objects.get(id=int(data['SaleId']))
            else:
                if type == 'C':
                    acquisition_detail.purchase = Purchase.objects.get(id=int(data['PurchaseId']))

                    product.returned_purchased_inventory = product.returned_purchased_inventory + \
                        int(a['Quantity'])
                    product.current_inventory = product.current_inventory - int(a['Quantity'])
                    product.save()

                    batch.total_quantity = batch.total_quantity - int(a['Quantity'])
                    batch.save()

                    data_batch_detail = {
                        'batch': batch,
                        'type': 'D',
                        'quantity': int(a['Quantity']),
                        'entry_date': formatted_time,
                        'acquisition_detail': acquisition_detail
                    }
                    batch_detail = BatchDetail.objects.create(**data_batch_detail)
                    batch_detail.save()

            acquisition_detail.save()

            if product.current_inventory <= product.minimum_inventory:
                product.status = 'S'
                product.save()
            else:
                if product.current_inventory > product.minimum_inventory:
                    product.status = 'A'
                    product.save()
        product_return.quantity_shipped = quantity_shipped
        product_return.save()

        now = datetime.now()
        devolutions = ProductReturn.objects.filter(
            return_date__year=now.year, return_date__month=now.month, return_date__day=now.day).order_by('-return_date')

        t = loader.get_template('vetstore/product-return-list.html')
        c = ({'devolutions': devolutions})

        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'success': True, 'title': '¡Bien hecho!',
               'message': 'El recibo se ha generado correctamente.'})
        return JsonResponse({'success': True, 'message': 'Encontrado!', 'list': t.render(c), 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def get_sale(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            sale = Sales.objects.get(id=pk)
        except Sales.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe la venta.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        t = loader.get_template('vetstore/acquisition-list.html')
        c = ({'sale': sale})
        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'info': True, 'title': 'Atento',
               'message': 'Verifique, antes de almacenar las modificaciones hechas a los datos.'})
        return JsonResponse({
            'success': True,
            'formupdate': t.render(c),
            'alert': t2.render(c2)
        })

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def get_purchase(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            purchase = Purchase.objects.get(id=pk)
        except Purchase.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe la compra.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        t = loader.get_template('vetstore/acquisition-list.html')
        c = ({'purchase': purchase})
        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'info': True, 'title': 'Atento',
               'message': 'Verifique, antes de almacenar las modificaciones hechas a los datos.'})
        return JsonResponse({
            'success': True,
            'formupdate': t.render(c),
            'alert': t2.render(c2)
        })

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def get_group_payments(request):
    if request.method == 'GET':

        start = parse_date(request.GET.get('start-date', ''))
        final = parse_date(request.GET.get('end-date', ''))
        mode = str(request.GET.get('mode', ''))
        branch_office_id = int(request.GET.get('branch-office-id', 0))

        print('mode: ', mode)

        if start is None:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'La fecha inicial esta vacia.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})
        else:
            purchases_subtotal_sum = 0
            purchases_total_sum = 0
            purchases_igv_sum = 0
            purchases_gain_sum = 0

            sales_charged_sum = 0
            sales_received_sum = 0
            sales_turned_sum = 0
            sales_gain_obtained_sum = 0
            sales_gain_estimated_sum = 0
            sales_total_discount_turned_sum = 0

            expenses_rode_sum = 0

            purchases = []
            sales = []
            expenses = []

            if mode == 'EQUALS':
                print('EQUALS: ')

                last = start + timedelta(days=1)
                first = start - timedelta(days=1)
                # first = start

                print('first: ', first)
                print('last: ', last)
                purchases = Purchase.objects.filter(
                    created_at__date__gt=first, created_at__date__lt=last).order_by('created_at')
                sales = Sales.objects.filter(
                    sale_date__gt=first, sale_date__lt=last).order_by('sale_date')
                expenses = Expense.objects.filter(
                    created_at__date__gt=first, created_at__date__lt=last).order_by('created_at')

                if branch_office_id > 0:
                    sales = sales.filter(branch_office_id=branch_office_id)
                    purchases = purchases.filter(branch_office_id=branch_office_id)
                    expenses = expenses.filter(branch_office_id=branch_office_id)

                purchases_total_sum = purchases.aggregate(Sum('total'))
                purchases_subtotal_sum = purchases.aggregate(Sum('subtotal'))
                purchases_igv_sum = purchases.aggregate(Sum('igv'))

                for purchase in purchases:
                    for detail in purchase.detail_purchases.all():
                        purchases_gain_sum += detail.gain

                sales_charged_sum = sales.aggregate(Sum('charged'))
                sales_received_sum = sales.aggregate(Sum('received'))
                sales_turned_sum = sales.aggregate(Sum('turned'))

                for sale in sales:
                    for detail in sale.detail_sales.all():
                        sales_gain_obtained_sum += detail.profit_per_product_in_sales_obtained
                        sales_gain_estimated_sum += detail.profit_per_product_in_sales_estimated
                        sales_total_discount_turned_sum += detail.discount_per_product_in_sales

                expenses_rode_sum = expenses.aggregate(Sum('rode'))

            else:
                if mode == 'GREATER_THAN':
                    print('GREATER_THAN: ')
                    first = start
                    print(first)

                    purchases = Purchase.objects.filter(
                        created_at__date__gt=first).order_by('created_at')
                    sales = Sales.objects.filter(sale_date__gt=first).order_by('sale_date')
                    expenses = Expense.objects.filter(
                        created_at__date__gt=first).order_by('created_at')

                    if branch_office_id > 0:
                        sales = sales.filter(branch_office_id=branch_office_id)
                        purchases = purchases.filter(branch_office_id=branch_office_id)
                        expenses = expenses.filter(branch_office_id=branch_office_id)

                    purchases_total_sum = purchases.aggregate(Sum('total'))
                    purchases_subtotal_sum = purchases.aggregate(Sum('subtotal'))
                    purchases_igv_sum = purchases.aggregate(Sum('igv'))

                    for purchase in purchases:
                        for detail in purchase.detail_purchases.all():
                            purchases_gain_sum += detail.gain

                    sales_charged_sum = sales.aggregate(Sum('charged'))
                    sales_received_sum = sales.aggregate(Sum('received'))
                    sales_turned_sum = sales.aggregate(Sum('turned'))

                    for sale in sales:
                        sales_gain_obtained_sum += sale.total_gain_obtained
                        sales_gain_estimated_sum += sale.total_gain_estimated
                        sales_total_discount_turned_sum += sale.total_discount

                    expenses_rode_sum = expenses.aggregate(Sum('rode'))
                else:
                    if mode == 'LESS_THAN':
                        print('LESS_THAN: ')

                        purchases = Purchase.objects.filter(
                            created_at__date__lt=start).order_by('created_at')
                        sales = Sales.objects.filter(sale_date__lt=start).order_by('sale_date')
                        expenses = Expense.objects.filter(
                            created_at__date__lt=start).order_by('created_at')

                        if branch_office_id > 0:
                            sales = sales.filter(branch_office_id=branch_office_id)
                            purchases = purchases.filter(branch_office_id=branch_office_id)
                            expenses = expenses.filter(branch_office_id=branch_office_id)

                        purchases_total_sum = purchases.aggregate(Sum('total'))
                        purchases_subtotal_sum = purchases.aggregate(Sum('subtotal'))
                        purchases_igv_sum = purchases.aggregate(Sum('igv'))
                        for purchase in purchases:
                            for detail in purchase.detail_purchases.all():
                                purchases_gain_sum += detail.gain

                        sales_charged_sum = sales.aggregate(Sum('charged'))
                        sales_received_sum = sales.aggregate(Sum('received'))
                        sales_turned_sum = sales.aggregate(Sum('turned'))

                        for sale in sales:
                            sales_gain_obtained_sum += sale.total_gain_obtained
                            sales_gain_estimated_sum += sale.total_gain_estimated
                            sales_total_discount_turned_sum += sale.total_discount

                        expenses_rode_sum = expenses.aggregate(Sum('rode'))

                    else:
                        if mode == 'BETWEEN':
                            print('BETWEEN: ')
                            if final is None:
                                t = loader.get_template('vetstore/alerts.html')
                                c = ({'danger': True, 'title': '¡Error!',
                                      'message': 'La fecha final esta vacia.'})
                                return JsonResponse({'success': False, 'alert': t.render(c)})
                            else:
                                if final < start:
                                    t = loader.get_template('vetstore/alerts.html')
                                    c = ({'danger': True, 'title': '¡Error!',
                                          'message': 'La fecha final es menor a la inicial.'})
                                    return JsonResponse({'success': False, 'alert': t.render(c)})
                                else:
                                    if final == start:
                                        t = loader.get_template('vetstore/alerts.html')
                                        c = ({'danger': True, 'title': '¡Error!',
                                              'message': 'La fecha final es igual a la inicial.'})
                                        return JsonResponse({'success': False, 'alert': t.render(c)})
                                print('final: ', final)
                                print('start: ', start)
                                # first = start + timedelta(days=1)
                                last = final + timedelta(days=1)

                                purchases = Purchase.objects.filter(created_at__date__gte=start).filter(
                                    created_at__date__lt=last).order_by('created_at')
                                sales = Sales.objects.filter(sale_date__gte=start).filter(
                                    sale_date__lt=last).order_by('sale_date')
                                expenses = Expense.objects.filter(created_at__date__gte=start).filter(
                                    created_at__date__lt=last).order_by('created_at')

                                if branch_office_id > 0:
                                    sales = sales.filter(branch_office_id=branch_office_id)
                                    purchases = purchases.filter(branch_office_id=branch_office_id)
                                    expenses = expenses.filter(branch_office_id=branch_office_id)

                                purchases_total_sum = purchases.aggregate(Sum('total'))
                                purchases_subtotal_sum = purchases.aggregate(Sum('subtotal'))
                                purchases_igv_sum = purchases.aggregate(Sum('igv'))

                                for purchase in purchases:
                                    for detail in purchase.detail_purchases.all():
                                        purchases_gain_sum += detail.gain

                                sales_charged_sum = sales.aggregate(Sum('charged'))
                                sales_received_sum = sales.aggregate(Sum('received'))
                                sales_turned_sum = sales.aggregate(Sum('turned'))

                                for sale in sales:
                                    sales_gain_obtained_sum += sale.total_gain_obtained
                                    sales_gain_estimated_sum += sale.total_gain_estimated
                                    sales_total_discount_turned_sum += sale.total_discount

                                expenses_rode_sum = expenses.aggregate(Sum('rode'))

            if not purchases and not sales and not expenses:
                t = loader.get_template('vetstore/alerts.html')
                c = ({'warning': True, 'title': '¡Atención!', 'message': 'Registros no encontrados.'})
                return JsonResponse({'success': False, 'alert': t.render(c)})

            t = loader.get_template('vetstore/group-payments.html')
            c = ({
                'purchases': purchases,
                'purchases_total_sum': purchases_total_sum,
                'purchases_subtotal_sum': purchases_subtotal_sum,
                'purchases_igv_sum': purchases_igv_sum,
                'purchases_gain_sum': purchases_gain_sum,

                'sales': sales,
                'sales_charged_sum': sales_charged_sum,
                'sales_received_sum': sales_received_sum,
                'sales_turned_sum': sales_turned_sum,
                'sales_gain_obtained_sum': sales_gain_obtained_sum,
                'sales_gain_estimated_sum': sales_gain_estimated_sum,
                'sales_total_discount_turned_sum': sales_total_discount_turned_sum,

                'expenses': expenses,
                'expenses_rode_sum': expenses_rode_sum

            })

            t2 = loader.get_template('vetstore/alerts.html')
            c2 = ({'success': True, 'title': '¡Bien hecho!', 'message': 'Busqueda exitosa.'})

            return JsonResponse({'success': True, 'list': t.render(c), 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def branch_registration(request):
    if request.method == 'POST':
        try:
            data = {
                'name': request.POST.get('name', ''),
            }
            brand = Brand.objects.create(**data)
            brand.save()
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'La marca se repite.'})

        brands = Brand.objects.all()
        employee = Employee.objects.get(user=request.user)
        role = employee.role.first().code
        # print 'role: ', employee.role.code
        t3 = loader.get_template('vetstore/brand-list.html')
        c3 = ({'brands': brands, 'role': role})

        t = loader.get_template('vetstore/alerts.html')
        c = ({'success': True, 'title': '¡Bien hecho!',
              'message': 'Los datos se han registrado correctamente.'})
        return JsonResponse({'success': True, 'alert': t.render(c), 'list': t3.render(c3)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def brand_update(request):
    if request.method == 'POST':
        brand_id = request.POST.get('brand-id', 0)
        try:
            brand = Brand.objects.get(pk=int(brand_id))
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No existe la marca.'})
        brand.name = str(request.POST.get('name', ''))
        brand.save()
        employee = Employee.objects.get(user=request.user)
        role = employee.role.first().code
        brands = Brand.objects.all()

        t3 = loader.get_template('vetstore/brand-list.html')
        c3 = ({'brands': brands, 'role': role})

        t = loader.get_template('vetstore/alerts.html')
        c = ({'success': True, 'title': '¡Bien hecho!',
              'message': 'Los datos se han actualizado correctamente.'})
        return JsonResponse({'success': True, 'alert': t.render(c), 'list': t3.render(c3)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


def go_back_brand(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        try:
            brand = Brand.objects.get(pk=pk)
        except Brand.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'No existe la marca.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        t = loader.get_template('vetstore/brand-update-form.html')
        c = ({'brand': brand})
        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'info': True, 'title': 'Atento',
               'message': 'Verifique, antes de almacenar las modificaciones hechas a los datos.'})
        return JsonResponse({
            'success': True,
            'formupdate': t.render(c),
            'alert': t2.render(c2)
        })

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def add_category(request):
    if request.method == 'GET':
        name = str(request.GET.get('name', ''))
        comment = str(request.GET.get('comment', ''))
        pid = int(request.GET.get('pid', 0))
        search = Category.objects.filter(name__exact=name)
        if search.count() > 0:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'Categoría repetida.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        data_category = {'name': name, 'comment': comment}
        category = Category.objects.create(**data_category)
        category.save()

        if pid != 0:
            try:
                parent = Category.objects.get(id=pid)
                category.parent = parent
                category.save()
            except Category.DoesNotExist:
                t = loader.get_template('vetstore/alerts.html')
                c = ({'danger': True, 'title': '¡Error!', 'message': 'Categoría no encontrada.'})
                return JsonResponse({'success': False, 'alert': t.render(c)})

        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'success': True, 'title': '¡Bien hecho!',
               'message': 'Categoría generada correctamente.'})
        return JsonResponse({'success': True, 'category': category.id, 'alert': t2.render(c2)})
    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def update_category(request):
    if request.method == 'GET':
        id = int(request.GET.get('id', 0))
        name = str(request.GET.get('name', ''))
        comment = str(request.GET.get('comment', ''))
        pid = int(request.GET.get('pid', 0))

        try:
            category = Category.objects.get(id=id)
        except Category.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'Categoría no encontrada.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        if pid != 0:
            parent = Category.objects.get(id=pid)
            category.parent = parent
            category.save()

        category.name = name
        category.comment = comment
        category.save()

        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'success': True, 'title': '¡Bien hecho!',
               'message': 'Categoría actualizada correctamente.'})
        return JsonResponse({'success': True, 'category': category.id, 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def delete_category(request):
    if request.method == 'GET':
        id = int(request.GET.get('id', 0))
        print('id:', id)
        try:
            category = Category.objects.get(id=id)
        except Category.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'Categoría no encontrada.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})
        category.delete()
        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'success': True, 'title': '¡Bien hecho!',
               'message': 'Categoría eliminada correctamente.'})
        return JsonResponse({'success': True, 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})


@csrf_exempt
def update_employee(request):
    if request.method == 'GET':
        pk = int(request.GET.get('pk', 0))
        code = int(request.GET.get('code', 0))

        try:
            employee = Employee.objects.get(user_id=pk)
        except Employee.DoesNotExist:
            t = loader.get_template('vetstore/alerts.html')
            c = ({'danger': True, 'title': '¡Error!', 'message': 'Empleado no encontrado.'})
            return JsonResponse({'success': False, 'alert': t.render(c)})

        if code != 0:
            employee.code = code
            employee.save()
        t2 = loader.get_template('vetstore/alerts.html')
        c2 = ({'success': True, 'title': '¡Bien hecho!',
               'message': 'Código actualizado correctamente.'})
        return JsonResponse({'success': True, 'alert': t2.render(c2)})

    t = loader.get_template('vetstore/alerts.html')
    c = ({'danger': True, 'title': '¡Error!',
          'message': 'Solicitud invalida, por favor vaya a la página anterior.'})
    return JsonResponse({'alert': t.render(c)})
