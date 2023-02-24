# Importing pandas
import pandas as pd
from django.http import HttpResponse, HttpResponseRedirect
from .models import Product, Client, Order, OrderDetail, SubsidiaryStore, ProductStore, Kardex
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user
from django.template import loader
import io
import requests


def kardex_glp_excel(request, pk):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    if request.method == 'GET':
        if pk != '':
            # other_subsidiary_store_obj = SubsidiaryStore.objects.get(id=int(pk))  # otro almacen insumos
            # my_subsidiary_store_glp_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj,
            #                                                           category='G')  # pluspetrol
            # my_subsidiary_store_insume_obj = SubsidiaryStore.objects.get(subsidiary=subsidiary_obj,
            #                                                              category='I')  # tu almacen insumos
            #
            # product_obj = Product.objects.get(is_approved_by_osinergmin=True, name__exact='GLP')
            # product_store_obj = ProductStore.objects.get(subsidiary_store=my_subsidiary_store_glp_obj, product=product_obj)
            #
            # kardex_set = Kardex.objects.filter(product_store=product_store_obj)
            #
            # tpl = loader.get_template('sales/kardex_glp_grid.html')
            # context = ({
            #     'is_pdf': True,
            #     'kardex_set': kardex_set,
            #     'my_subsidiary_store_insume': my_subsidiary_store_insume_obj,
            #     'other_subsidiary_store': other_subsidiary_store_obj,
            # })

            # Create the HttpResponse object with the appropriate CSV header.
            # response = HttpResponse(content_type='text/csv')
            # response['Content-Disposition'] = 'attachment; filename="kardex_csv.csv"'
            #
            # response.write(tpl.render(context))
            # return response

            # # The webpage URL whose table we want to extract
            # url = "http://localhost:8001/sales/get_only_grid_kardex_glp/"+str(pk)+"/"
            url = "https://www.geeksforgeeks.org/extended-operators-in-relational-algebra/"
            # # Assign the table data to a Pandas dataframe
            r = requests.get(url).content
            table = pd.read_html(r)[0]
            # # Print the dataframe
            table.to_excel("data.xlsx")

            response = HttpResponse(table)
            return response
            # print(table)