from django.contrib import admin

from .models import ApiAccessEvent, ApiCredential, AssistantDraft, AssistantDraftEvent


@admin.register(ApiCredential)
class ApiCredentialAdmin(admin.ModelAdmin):
    list_display = ("name", "token_prefix", "authorized_user", "created_at", "expires_at", "revoked_at")
    readonly_fields = tuple(field.name for field in ApiCredential._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ApiAccessEvent)
class ApiAccessEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "actor", "endpoint", "status_code", "result_count", "created_at")
    readonly_fields = tuple(field.name for field in ApiAccessEvent._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AssistantDraft)
class AssistantDraftAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "requested_by", "contract", "status", "created_at")
    readonly_fields = tuple(field.name for field in AssistantDraft._meta.fields)

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(AssistantDraftEvent)
class AssistantDraftEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "actor", "contract", "created_at")
    readonly_fields = tuple(field.name for field in AssistantDraftEvent._meta.fields)

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
