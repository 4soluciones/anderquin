from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from apps.comercial import models
# Register your models here.


class TowingBrandAdmin(ImportExportModelAdmin):
    list_display = ('name',)


admin.site.register(models.TowingBrand, TowingBrandAdmin)


class TowingModelAdmin(ImportExportModelAdmin):
    list_display = ('name', 'towing_brand')


admin.site.register(models.TowingModel, TowingModelAdmin)


class TruckBrandAdmin(ImportExportModelAdmin):
    list_display = ('name',)


admin.site.register(models.TruckBrand, TruckBrandAdmin)


class TruckModelAdmin(ImportExportModelAdmin):
    list_display = ('name', 'truck_brand')


admin.site.register(models.TruckModel, TruckModelAdmin)


class OwnerAdmin(ImportExportModelAdmin):
    list_display = ('name',)


admin.site.register(models.Owner, OwnerAdmin)

