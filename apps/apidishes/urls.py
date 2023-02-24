from django.urls import path
from rest_framework import routers
from apps.apidishes.views import *

router = routers.DefaultRouter()

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('snippet/subcategories-list/', subcategories_list),
    path('snippet/complement-list-by-subcategory/<int:subcat>/', complements_list),
    path('snippet/dishes-list/<int:subcat>/', dishes_list),
    path('snippet/orders-list/', orders_list),
    path('snippet/persons-list/', persons_list),
    path('snippet/persons-list/<int:type>/', persons_list),
    path('snippet/address-list-by-customer/<int:customer_id>/', address_list_by_customer),
    path('snippet/new-address/', new_address),
]
