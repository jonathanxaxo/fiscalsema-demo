from django.urls import path

from .views import (
    AssistantDraftBatchCreateView, AssistantDraftCreateView, AssistantDraftDetailApiView, ContractAccountabilityView, ContractAllocationListView,
    ContractCommitmentListView, ContractDetailView, ContractDocumentListView,
    ContractExecutionListView, ContractFinancialSummaryView, ContractInvoiceListView,
    ContractItemListView, ContractListView, ContractPaymentListView, ContractReportView,
    CapabilityView, ContractSummaryView, ContractWorkOrderListView, DocumentContentView, InvoiceCheckView,
)


app_name = "api_v1"
urlpatterns = [
    path("capabilities/", CapabilityView.as_view(), name="capabilities"),
    path("contracts/", ContractListView.as_view(), name="contract-list"),
    path("contracts/<int:contract_id>/", ContractDetailView.as_view(), name="contract-detail"),
    path("contracts/<int:contract_id>/summary/", ContractSummaryView.as_view(), name="contract-summary"),
    path("contracts/<int:contract_id>/commitments/", ContractCommitmentListView.as_view(), name="commitment-list"),
    path("contracts/<int:contract_id>/items/", ContractItemListView.as_view(), name="item-list"),
    path("contracts/<int:contract_id>/work-orders/", ContractWorkOrderListView.as_view(), name="work-order-list"),
    path("contracts/<int:contract_id>/allocations/", ContractAllocationListView.as_view(), name="allocation-list"),
    path("contracts/<int:contract_id>/executions/", ContractExecutionListView.as_view(), name="execution-list"),
    path("contracts/<int:contract_id>/invoices/", ContractInvoiceListView.as_view(), name="invoice-list"),
    path("contracts/<int:contract_id>/payments/", ContractPaymentListView.as_view(), name="payment-list"),
    path("contracts/<int:contract_id>/documents/", ContractDocumentListView.as_view(), name="document-list"),
    path("contracts/<int:contract_id>/financial-summary/", ContractFinancialSummaryView.as_view(), name="financial-summary"),
    path("contracts/<int:contract_id>/accountability/", ContractAccountabilityView.as_view(), name="accountability"),
    path("contracts/<int:contract_id>/report/", ContractReportView.as_view(), name="report"),
    path("invoices/<int:invoice_id>/check/", InvoiceCheckView.as_view(), name="invoice-check"),
    path("documents/<int:document_id>/content/", DocumentContentView.as_view(), name="document-content"),
    path("drafts/", AssistantDraftCreateView.as_view(), name="draft-create"),
    path("drafts/batch/", AssistantDraftBatchCreateView.as_view(), name="draft-batch-create"),
    path("drafts/<int:draft_id>/", AssistantDraftDetailApiView.as_view(), name="draft-detail"),
]
