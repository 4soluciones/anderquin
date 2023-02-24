from rest_framework import serializers
from apps.dishes.models import *


class SubcategorySerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Subcategory
        fields = ('id', 'name', 'description', 'category', 'image', 'thumbnail_url', 'complement')

    def get_thumbnail_url(self, subcategory):
        request = self.context.get('request')
        thumbnail_url = subcategory.image_thumbnail.url
        return request.build_absolute_uri(thumbnail_url)


class ComplementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Complement
        fields = ('id', 'name', 'price')


class DishSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = ('id', 'name', 'price', 'subcategory', 'image', 'thumbnail_url')

    def get_thumbnail_url(self, dish):
        request = self.context.get('request')
        thumbnail_url = dish.image_thumbnail.url
        return request.build_absolute_uri(thumbnail_url)


class PersonSerializer(serializers.ModelSerializer):

    class Meta:
        model = Person
        fields = '__all__'


class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = '__all__'


class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = '__all__'
