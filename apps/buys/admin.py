from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from apps.buys import models


# Register your models here.

class MoneyChangeAdmin(admin.ModelAdmin):
    list_display = ('search_date', 'sunat_date', 'sell', 'buy')


admin.site.register(models.Purchase)
admin.site.register(models.MoneyChange, MoneyChangeAdmin)


@admin.register(models.AdminSupplier)
class AdminSupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'ruc', 'phone', 'is_enabled')
    search_fields = ('name', 'ruc')
    list_filter = ('is_enabled',)


class AdministrativePurchaseDetailInline(admin.TabularInline):
    model = models.AdministrativePurchaseDetail
    extra = 0


@admin.register(models.AdministrativePurchase)
class AdministrativePurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_date', 'document_number', 'get_supplier_display', 'currency', 'total')
    list_filter = ('purchase_date', 'currency')
    search_fields = ('document_number', 'supplier_name_free')
    inlines = [AdministrativePurchaseDetailInline]
