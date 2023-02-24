from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from imagekit.admin import AdminThumbnail
from apps.dishes import models
# Register your models here.

admin.site.register(models.Subsidiary)
admin.site.register(models.Category)
admin.site.register(models.Subcategory)
admin.site.register(models.Complement)


# Admin Action Functions
def make_active(modeladmin, request, queryset):
    queryset.update(status=True)


# Action description
make_active.short_description = "Mark selected records as active"
# users who have change permission can view this action
make_active.allowed_permissions = ('change',)


def softdelete_selected(modeladmin, request, queryset):
    queryset.update(status=False)


# Action description
softdelete_selected.short_description = "Delete Selected records"
# users who have change permission can view this action
softdelete_selected.allowed_permissions = ('change',)


class SubsidiaryAdmin(ImportExportModelAdmin):
    pass


class CategoryAdmin(ImportExportModelAdmin):
    pass


class SubcategoryAdmin(ImportExportModelAdmin):
    pass


class SubcategoryInstanceInline (admin.TabularInline):
    model = models.Subcategory


# Define the admin class
class DishAdmin(ImportExportModelAdmin):
    list_display = ('name', 'price', 'subcategory', 'quantity',
                    'admin_thumbnail', 'image', 'status')
    admin_thumbnail = AdminThumbnail(image_field='image_thumbnail')
    ordering = ('id',)
    search_fields = ('name', 'subcategory')
    list_filter = ('subcategory', 'quantity')
    #   Show these actions in list view dropdown menu
    actions = [make_active, softdelete_selected]
    list_editable = ['price', 'image', 'status']

    # set delete permission to false to remove delete button from the detail page
    def has_delete_permission(self, request, obj=None):
        return False


# Register the admin class with the associated model
admin.site.register(models.Dish, DishAdmin)
