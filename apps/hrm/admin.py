from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from apps.hrm import models
# Register your models here.


class DocumentTypeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description', 'short_description', 'is_available')
    ordering = ('id',)
    list_editable = ['is_available', ]


admin.site.register(models.DocumentType, DocumentTypeAdmin)


class DocumentIssuingCountryAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description')
    ordering = ('id',)


admin.site.register(models.DocumentIssuingCountry, DocumentIssuingCountryAdmin)


class NationalityAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description')
    ordering = ('id',)


admin.site.register(models.Nationality, NationalityAdmin)


class RoadTypeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description')
    ordering = ('id',)


admin.site.register(models.RoadType, RoadTypeAdmin)


class ZoneTypeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description')
    ordering = ('id',)


admin.site.register(models.ZoneType, ZoneTypeAdmin)


class DepartmentAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description')
    ordering = ('id',)


admin.site.register(models.Department, DepartmentAdmin)


class ProvinceAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description')
    ordering = ('id',)


admin.site.register(models.Province, ProvinceAdmin)


class DistrictAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description')
    ordering = ('id',)


admin.site.register(models.District, DistrictAdmin)


class TelephoneNationalLongDistanceCodeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description')
    ordering = ('id',)


admin.site.register(models.TelephoneNationalLongDistanceCode,
                    TelephoneNationalLongDistanceCodeAdmin)


class EmployeeAdmin(ImportExportModelAdmin):
    list_display = ('document_type', 'document_number', 'document_issuing_country',
                    'birthdate', 'paternal_last_name', 'maternal_last_name', 'names')
    ordering = ('paternal_last_name',)


admin.site.register(models.Employee, EmployeeAdmin)


class LaborRegimeAdmin(ImportExportModelAdmin):
    list_display = ('id', 'description', 'short_description',
                    'private_sector', 'public_sector', 'other_entities')
    ordering = ('id',)


admin.site.register(models.LaborRegime, LaborRegimeAdmin)

admin.site.register(models.Subsidiary)

