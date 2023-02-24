from django.contrib.auth.models import User
from rest_framework import serializers
from apps.vetstore.models import *


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class BranchOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchOffice
        fields = '__all__'


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return '{} {}'.format(obj.user.first_name, obj.user.last_name)

    class Meta:
        model = Employee
        fields = ('pk', 'full_name', 'get_branch_office')
