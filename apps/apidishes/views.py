from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .serializers import *
from rest_framework.parsers import JSONParser
from rest_framework import viewsets
from rest_framework import status
from apps.dishes.models import *
# Create your views here.


@csrf_exempt
def complements_list(request, subcat):
    """
    Retrieve, update or delete a code snippet.
    """
    try:
        subcategory = Subcategory.objects.get(pk=subcat)
    except Subcategory.DoesNotExist:
        return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Returns all complements objects for this Subcategory.
        complements = subcategory.complement.all()
        serializer = ComplementSerializer(complements, many=True)
        return JsonResponse(serializer.data, safe=False)


@csrf_exempt
def subcategories_list(request):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        subcategories = Subcategory.objects.filter(status=True).order_by("id")
        serializer = SubcategorySerializer(subcategories, many=True, context={"request": request})
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = SubcategorySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def complement_list_by_subcategory(request):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        complements = Complement.objects.all().order_by("id")
        serializer = ComplementSerializer(complements, many=True, context={"request": request})
        return JsonResponse(serializer.data, safe=False)


@csrf_exempt
def dishes_list(request, subcat):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        dishes = Dish.objects.filter(status=True).filter(subcategory=subcat).order_by("id")
        serializer = DishSerializer(dishes, many=True, context={"request": request})
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = DishSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def orders_list(request):

    if request.method == 'GET':
        orders = Order.objects.filter(status='N').order_by("id")
        serializer = OrderSerializer(orders, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = OrderSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def address_list_by_customer(request, customer_id):
    try:
        customer = Customer.objects.get(pk=customer_id)
    except Customer.DoesNotExist:
        return HttpResponse(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        address = Address.objects.filter(customer=customer).order_by("id")
        serializer = AddressSerializer(address, many=True)
        return JsonResponse(serializer.data, safe=False)


@csrf_exempt
def new_address(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = AddressSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
    return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def persons_list(request, type=0):

    if request.method == 'GET':
        persons = Person.objects.all().order_by("id")
        serializer = PersonSerializer(persons, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = PersonSerializer(data=data)
        if serializer.is_valid() and type != 0:
            if type == 1:  # Customer
                person = serializer.save()
                customer = Customer.objects.create(person=person, )
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
            elif type == 2:  # Employee
                print(serializer)
                # serializer.save()
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
