import json
from django.http import JsonResponse, Http404, HttpResponse

from apps.vetstore.serializers import *

from rest_framework import viewsets
from rest_framework import status
from apps.vetstore.models import *


def get_brand(request):
    brand = Brand.objects.all()
    brand_serializer = BrandSerializer(brand, many=True)
    data_json = json.dumps(brand_serializer.data)
    mimetype = "application/json"
    return HttpResponse(data_json, mimetype)


def get_category(request):
    category = Category.objects.all()
    category_serializer = CategorySerializer(category, many=True)
    data_json = json.dumps(category_serializer.data)
    mimetype = "application/json"
    return HttpResponse(data_json, mimetype)


def get_branch_office(request):
    branch_office = BranchOffice.objects.all()
    branch_office_serializer = BranchOfficeSerializer(branch_office, many=True)
    data_json = json.dumps(branch_office_serializer.data)
    mimetype = "application/json"
    return HttpResponse(data_json, mimetype)


def get_employee(request):
    employee = Employee.objects.all()
    employee_serializer = EmployeeSerializer(employee, many=True)
    data_json = json.dumps(employee_serializer.data)
    mimetype = "application/json"
    return HttpResponse(data_json, mimetype)
