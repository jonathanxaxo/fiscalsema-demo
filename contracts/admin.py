from django.contrib import admin

from .models import (
    BudgetCommitment,
    BudgetCommitmentEvent,
    CommitmentMovement,
    Contract,
    ContractAccess,
    ContractEvent,
    CsvExportEvent,
    ContractInvitation,
    ContractSharingEvent,
    FiscalSubstitution,
    FiscalSubstitutionEvent,
    ContractItem,
    ContractItemEvent,
    Invoice,
    InvoiceEvent,
    Payment,
    PaymentEvent,
    WorkOrder,
    WorkOrderEvent,
    WorkOrderAllocation,
    WorkOrderAllocationEvent,
    WorkOrderExecution,
    WorkOrderExecutionEvent,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Contract)
class ContractAdmin(ReadOnlyAdmin):
    list_display = (
        "number",
        "supplier_name",
        "contracting_organization",
        "responsible_fiscal",
        "status",
        "validity_end",
        "archived_at",
    )
    list_filter = ("status", "contracting_organization", "archived_at")
    search_fields = ("number", "process_number", "object", "supplier_name", "supplier_tax_id")


@admin.register(ContractEvent)
class ContractEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "contract", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("contract__number", "actor__email")


@admin.register(CsvExportEvent)
class CsvExportEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "contract", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("contract__number", "actor__email")


@admin.register(ContractAccess)
class ContractAccessAdmin(ReadOnlyAdmin):
    list_display = ("contract", "user", "access_type", "status", "granted_by", "granted_at")
    list_filter = ("access_type", "status", "granted_at")
    search_fields = ("contract__number", "user__email", "granted_by__email")


@admin.register(ContractInvitation)
class ContractInvitationAdmin(ReadOnlyAdmin):
    list_display = ("contract", "email", "access_type", "status", "invited_by", "invited_at")
    list_filter = ("access_type", "status", "invited_at")
    search_fields = ("contract__number", "email", "invited_by__email")


@admin.register(ContractSharingEvent)
class ContractSharingEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "contract", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("contract__number", "actor__email")


@admin.register(FiscalSubstitution)
class FiscalSubstitutionAdmin(ReadOnlyAdmin):
    list_display = (
        "contract",
        "email",
        "substitute",
        "starts_on",
        "ends_on",
        "status",
        "created_by",
    )
    list_filter = ("status", "starts_on", "ends_on")
    search_fields = ("contract__number", "email", "substitute__email")


@admin.register(FiscalSubstitutionEvent)
class FiscalSubstitutionEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "contract", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("contract__number", "actor__email", "substitution__email")


@admin.register(ContractItem)
class ContractItemAdmin(ReadOnlyAdmin):
    list_display = (
        "number",
        "contract",
        "category",
        "unit",
        "contracted_quantity",
        "unit_value",
        "is_active",
    )
    list_filter = ("is_active", "unit", "category")
    search_fields = ("number", "description", "category", "contract__number")


@admin.register(ContractItemEvent)
class ContractItemEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "item", "contract", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("item__number", "contract__number", "actor__email")


@admin.register(BudgetCommitment)
class BudgetCommitmentAdmin(ReadOnlyAdmin):
    list_display = (
        "number",
        "ped",
        "contract",
        "commitment_date",
        "initial_value",
        "is_active",
    )
    list_filter = ("is_active", "commitment_date", "source")
    search_fields = ("number", "ped", "source", "contract__number")


@admin.register(CommitmentMovement)
class CommitmentMovementAdmin(ReadOnlyAdmin):
    list_display = (
        "movement_type",
        "commitment",
        "movement_date",
        "amount",
        "created_by",
    )
    list_filter = ("movement_type", "movement_date")
    search_fields = ("commitment__number", "commitment__contract__number")


@admin.register(BudgetCommitmentEvent)
class BudgetCommitmentEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "commitment", "contract", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("commitment__number", "contract__number", "actor__email")


@admin.register(WorkOrder)
class WorkOrderAdmin(ReadOnlyAdmin):
    list_display = (
        "number",
        "contract",
        "item",
        "responsible",
        "opening_date",
        "deadline",
        "status",
    )
    list_filter = ("status", "opening_date", "deadline")
    search_fields = (
        "number",
        "process_number",
        "description",
        "responsible",
        "contract__number",
        "item__number",
    )


@admin.register(WorkOrderEvent)
class WorkOrderEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "work_order", "contract", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("work_order__number", "contract__number", "actor__email")


@admin.register(WorkOrderAllocation)
class WorkOrderAllocationAdmin(ReadOnlyAdmin):
    list_display = ("work_order", "commitment", "amount", "allocation_date", "status")
    list_filter = ("status", "allocation_date")
    search_fields = (
        "work_order__number",
        "commitment__number",
        "work_order__contract__number",
    )


@admin.register(WorkOrderAllocationEvent)
class WorkOrderAllocationEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "allocation", "work_order", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("work_order__number", "allocation__commitment__number", "actor__email")


@admin.register(WorkOrderExecution)
class WorkOrderExecutionAdmin(ReadOnlyAdmin):
    list_display = (
        "work_order", "execution_date", "competence", "executed_quantity",
        "executed_value", "created_by",
    )
    list_filter = ("execution_date", "competence")
    search_fields = ("work_order__number", "work_order__contract__number", "notes")


@admin.register(WorkOrderExecutionEvent)
class WorkOrderExecutionEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "execution", "work_order", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("work_order__number", "actor__email")


@admin.register(Invoice)
class InvoiceAdmin(ReadOnlyAdmin):
    list_display = (
        "number", "series", "contract", "work_order", "supplier_name",
        "issue_date", "gross_value", "accepted_value", "status",
    )
    list_filter = ("issue_date", "competence", "status")
    search_fields = (
        "number", "series", "supplier_name", "supplier_tax_id",
        "contract__number", "work_order__number", "process_number",
    )


@admin.register(InvoiceEvent)
class InvoiceEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "invoice", "work_order", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("invoice__number", "work_order__number", "actor__email")


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = (
        "invoice", "amount", "payment_date", "competence", "status", "created_by",
    )
    list_filter = ("payment_date", "competence", "status")
    search_fields = (
        "invoice__number", "invoice__contract__number", "process_number",
        "attestation_reference", "raer_reference", "homologation_reference",
    )


@admin.register(PaymentEvent)
class PaymentEventAdmin(ReadOnlyAdmin):
    list_display = ("event_type", "payment", "invoice", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("invoice__number", "invoice__contract__number", "actor__email")
