import logging

from django.db import connection
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET


logger = logging.getLogger(__name__)


@require_GET
@login_required
def home(request):
    from accounts.models import RegistrationRequest, RegistrationStatus
    from contracts.dashboard import build_contract_dashboard
    from contracts.services import (
        actor_is_active_fiscal,
        contracts_visible_to,
        contracts_writable_by,
        contract_is_read_only_for,
    )

    from accounts.models import UserProfile

    if request.user.profile == UserProfile.ADMINISTRATOR:
        from .admin_dashboard import build_admin_dashboard

        admin_dashboard = build_admin_dashboard()
        return render(
            request,
            "core/admin_home.html",
            {
                "admin_dashboard": admin_dashboard,
                "pending_registration_count": admin_dashboard["pending_count"],
            },
        )

    contracts = contracts_visible_to(request.user)
    selected_contract = None
    selected_id = request.GET.get("contract")
    if selected_id:
        if not selected_id.isdecimal():
            raise Http404("Contrato não encontrado.")
        selected_contract = get_object_or_404(contracts, pk=selected_id)
    else:
        selected_contract = contracts.first()
    dashboard = (
        build_contract_dashboard(selected_contract) if selected_contract else None
    )
    pending_registration_count = 0
    if request.user.has_perm("accounts.review_registration"):
        pending_registration_count = RegistrationRequest.objects.filter(
            status=RegistrationStatus.PENDING
        ).count()
    return render(
        request,
        "home.html",
        {
            "contracts": contracts,
            "selected_contract": selected_contract,
            "dashboard": dashboard,
            "pending_registration_count": pending_registration_count,
            "can_create_contract": (
                actor_is_active_fiscal(request.user)
                and request.user.has_perm("contracts.add_contract")
            ),
            "can_create_item": (
                bool(selected_contract)
                and contracts_writable_by(request.user)
                .filter(pk=selected_contract.pk)
                .exists()
            ),
            "is_read_only_access": (
                bool(selected_contract)
                and contract_is_read_only_for(request.user, selected_contract)
            ),
            "is_substitute_access": (
                bool(selected_contract)
                and selected_contract.responsible_fiscal_id != request.user.pk
                and contracts_writable_by(request.user)
                .filter(pk=selected_contract.pk)
                .exists()
            ),
            "contract_dashboard_mode": False,
        },
    )


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.warning("Health check do banco falhou")
        return JsonResponse({"status": "indisponivel", "database": "erro"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
