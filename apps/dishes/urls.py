from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.dishes.views import *
# from . import views, viewsets
urlpatterns = [
    path('subsidiary_create/', login_required(SubsidiaryCreate.as_view()), name='subsidiary_create'),
    path('subsidiary_list/', login_required(SubsidiaryList.as_view()), name='subsidiary_list'),
    path('subsidiary_edit/<int:pk>/', login_required(SubsidiaryUpdate.as_view()), name='subsidiary_edit'),
    path('subsidiary_delete/<int:pk>/', login_required(SubsidiaryDelete.as_view()), name='subsidiary_delete'),
    path('category_create/', login_required(CategoryCreate.as_view()), name='category_create'),
    path('category_list/', login_required(CategoryList.as_view()), name='category_list'),
    path('category_edit/<int:pk>/', login_required(CategoryUpdate.as_view()), name='category_edit'),
    path('category_delete/<int:pk>/', login_required(CategoryDelete.as_view()), name='category_delete'),
    path('subcategory_create/', login_required(SubcategoryCreate.as_view()), name='subcategory_create'),
    path('subcategory_list/', login_required(SubcategoryList.as_view()), name='subcategory_list'),
    path('subcategory_edit/<int:pk>/', login_required(SubcategoryUpdate.as_view()), name='subcategory_edit'),
    path('subcategory_delete/<int:pk>/',
         login_required(SubcategoryDelete.as_view()), name='subcategory_delete'),

    path('dish_list/', login_required(DishList.as_view()), name='dish_list'),
    path('json_dish_list/', login_required(JsonDishList.as_view()), name='json_dish_list'),
    path('json_dish_create/', login_required(JsonDishCreate.as_view()), name='json_dish_create'),
    path('json_dish_edit/<int:pk>/', login_required(JsonDishUpdate.as_view()), name='json_dish_edit'),
    path('json_dish_delete/<int:pk>/', login_required(JsonDishDelete.as_view()), name='json_dish_delete'),

    path('get_dishes/', get_dishes, name='get_dishes'),
]
