from django.contrib import admin

from .models import ImportEvent, SpreadsheetImport


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SpreadsheetImport)
class SpreadsheetImportAdmin(ReadOnlyAdmin):
    list_display = ("file_name", "entity_type", "contract", "status", "created_by", "created_at")
    list_filter = ("entity_type", "status")
    search_fields = ("file_name", "content_sha256", "contract__number")


@admin.register(ImportEvent)
class ImportEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "spreadsheet_import", "contract", "actor", "created_at")
    list_filter = ("event_type",)
