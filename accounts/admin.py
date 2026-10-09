from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import AccountChangeForm, AccountCreationForm
from .models import AuthenticationEvent, RegistrationRequest, User


@admin.register(User)
class AccountAdmin(UserAdmin):
    add_form = AccountCreationForm
    form = AccountChangeForm
    model = User
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "organization",
        "sector",
        "profile",
        "status",
        "is_staff",
        "last_login",
    )
    list_filter = ("profile", "status", "organization", "sector", "must_change_password")
    search_fields = (
        "email",
        "full_name",
        "organization__name",
        "sector__name",
        "organization_name",
        "sector_name",
    )
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Identidade",
            {
                "fields": (
                    "full_name",
                    "organization_name",
                    "sector_name",
                    "organization",
                    "sector",
                    "phone",
                    "profile",
                    "status",
                )
            },
        ),
        ("Primeiro acesso", {"fields": ("must_change_password",)}),
        (
            "Permissões técnicas",
            {"fields": ("is_superuser", "groups", "user_permissions")},
        ),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "organization_name",
                    "sector_name",
                    "organization",
                    "sector",
                    "phone",
                    "profile",
                    "status",
                    "must_change_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        # A criação operacional precisa passar pelo fluxo auditado da Etapa 12.
        return False

    def has_delete_permission(self, request, obj=None):
        # Contas são preservadas para manter vínculos e trilhas de auditoria.
        return False


@admin.register(AuthenticationEvent)
class AuthenticationEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__email", "user__full_name")
    readonly_fields = (
        "event_type",
        "user",
        "identifier_hash",
        "source_hash",
        "created_at",
        "details",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "created_at", "reviewed_at", "reviewed_by", "archived_at")
    list_filter = ("status", "created_at", "archived_at")
    search_fields = ("user__email", "user__full_name", "user__organization_name")
    readonly_fields = (
        "user",
        "status",
        "created_at",
        "reviewed_at",
        "reviewed_by",
        "rejection_reason",
        "archived_at",
        "archived_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
