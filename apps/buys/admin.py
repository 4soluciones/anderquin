from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from apps.buys import models

# Register your models here.
from apps.buys.models import AddressEntityReference, EntityReference, PurchaseDetail


class MoneyChangeAdmin(admin.ModelAdmin):
    list_display = ('search_date', 'sunat_date', 'sell', 'buy')


admin.site.register(models.Purchase)
admin.site.register(models.MoneyChange, MoneyChangeAdmin)


class AddressEntityReferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'entity_reference', 'address')


admin.site.register(AddressEntityReference, AddressEntityReferenceAdmin)


class EntityReferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'business_name', 'ruc')


admin.site.register(EntityReference, EntityReferenceAdmin)


class PurchaseDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase', 'product', 'quantity', 'unit', 'price_unit')

admin.site.register(PurchaseDetail, PurchaseDetailAdmin)