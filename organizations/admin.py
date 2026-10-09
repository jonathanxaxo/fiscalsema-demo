from django.contrib import admin

from .models import Organization, OrganizationEvent, Sector


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Organization)
class OrganizationAdmin(ReadOnlyAdmin):
    list_display = ("name", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Sector)
class SectorAdmin(ReadOnlyAdmin):
    list_display = ("name", "organization", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "organization")
    search_fields = ("name", "organization__name")


@admin.register(OrganizationEvent)
class OrganizationEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "organization", "sector", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("organization__name", "sector__name", "actor__email")
