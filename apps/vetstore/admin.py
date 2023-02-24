from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from imagekit.admin import AdminThumbnail
# Register your models here.
from apps.vetstore import models
# Register your models here.


admin.site.register(models.Brand)


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'comment', 'barcode', 'factory_barcode',
                    'sale_price', 'pass_price', 'admin_thumbnail', 'image')
    admin_thumbnail = AdminThumbnail(image_field='image_thumbnail')


admin.site.register(models.Product, ProductAdmin)


admin.site.register(models.Supplier)

admin.site.register(models.Customer)

admin.site.register(models.Role)


class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'schedule', 'code')
    list_editable = ['code', ]


admin.site.register(models.Employee, EmployeeAdmin)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'comment', 'parent')


admin.site.register(models.Category, CategoryAdmin)


admin.site.register(models.BranchOffice)


class BranchOfficeAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone', 'image')
    list_editable = ('name', 'address', 'phone')


class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'type', 'comment', 'date_assigned')


admin.site.register(models.Attendance, AttendanceAdmin)


admin.site.register(models.Schedule)


class SaleAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'status', 'customer', 'employee',
                    'charged', 'received', 'turned', 'branch_office')


admin.site.register(models.Sales, SaleAdmin)


class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'supplier', 'subtotal', 'igv',
                    'total', 'operation_number', 'request_date')


admin.site.register(models.Purchase, PurchaseAdmin)


class AcquisitionDetailAdmin(admin.ModelAdmin):
    list_display = ('rate', 'quantity_ordered', 'quantity_received',
                    'amount', 'product', 'purchase')


admin.site.register(models.AcquisitionDetail, AcquisitionDetailAdmin)


class BatchAdmin(admin.ModelAdmin):
    list_display = ('product', 'barcode', 'entry_date', 'total_quantity')


admin.site.register(models.Batch, BatchAdmin)


class BatchDetailAdmin(admin.ModelAdmin):
    list_display = ('batch', 'type', 'entry_date', 'quantity', 'acquisition_detail')


admin.site.register(models.BatchDetail, BatchDetailAdmin)


class DurationAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'day_week', 'start_working_day', 'end_working_day',
                    'start_time', 'end_time', 'snack_start_time', 'snack_end_time')
    list_editable = ('start_working_day', 'end_working_day', 'start_time',
                     'end_time', 'snack_start_time', 'snack_end_time',)


admin.site.register(models.Duration, DurationAdmin)


admin.site.register(models.WayPay)
