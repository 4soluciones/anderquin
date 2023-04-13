from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from apps.buys import models


# Register your models here.


class MoneyChangeAdmin(admin.ModelAdmin):
    list_display = ('search_date', 'sunat_date', 'sell', 'buy')


admin.site.register(models.Purchase)
admin.site.register(models.MoneyChange, MoneyChangeAdmin)
