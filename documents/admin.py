from django.contrib import admin

from .models import Document, DocumentEvent


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "contract", "version", "uploaded_by", "uploaded_at")
    list_filter = ("document_type", "related_entity_type", "uploaded_at")
    search_fields = ("title", "original_name", "sha256", "contract__number")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentEvent)
class DocumentEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "document", "contract", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("document__title", "contract__number", "actor__email")
    readonly_fields = ("event_type", "document", "contract", "actor", "created_at", "details")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
