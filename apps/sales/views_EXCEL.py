# Importing pandas
import pandas as pd
from django.http import HttpResponse, HttpResponseRedirect
from .models import Product, Client, Order, OrderDetail, SubsidiaryStore, ProductStore, Kardex
from django.contrib.auth.models import User
from apps.hrm.views import get_subsidiary_by_user
from django.template import loader
import io
import requests
