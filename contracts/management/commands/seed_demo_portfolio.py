"""Cria uma carteira fictícia coerente para demonstrar todos os perfis."""

import os
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    ADMINISTRATOR_PROFILES,
    FISCAL_TITULAR_PROFILES,
    AccountStatus,
    DemoProfileSwitch,
    User,
    UserProfile,
)
from contracts.intelligence import (
    confirm_contract_classification,
    run_contract_intelligence,
)
from contracts.governance import (
    apply_control_pack,
    create_contract_change,
    create_external_record,
    create_obligation,
    create_receipt,
    create_risk,
    update_alert_policy,
)
from contracts.models import (
    Contract,
    ContractAccess,
    ContractAlertPolicy,
    ContractAccessStatus,
    ContractChange,
    ContractChangeStatus,
    ContractChangeType,
    ContractChecklistItem,
    ContractClassification,
    ContractExternalRecord,
    ContractExternalRecordStatus,
    ContractExternalSystem,
    ContractManagementCategory,
    ContractObligation,
    ContractObligationCategory,
    ContractObligationStatus,
    ContractReceipt,
    ContractReceiptResult,
    ContractReceiptType,
    ContractRisk,
    ContractRiskLevel,
    ContractRiskStatus,
    IntelligenceReviewStatus,
)
from contracts.services import (
    contracts_visible_to,
    create_contract,
    share_contract_read_only,
)

from .seed_demo_presentation import MARKER, seed_contract_presentation

PORTFOLIO_MARKER = "[DEMO-CARTEIRA]"
GOVERNANCE_MARKER = "[DEMO-GOVERNANCA]"
CATEGORIES = (
    (
        ContractManagementCategory.SYSTEM,
        "Sustentação de sistema de gestão ambiental",
    ),
    (
        ContractManagementCategory.EQUIPMENT,
        "Aquisição de equipamentos de tecnologia",
    ),
    (
        ContractManagementCategory.CONTINUOUS_SERVICE,
        "Serviço continuado de suporte especializado",
    ),
    (
        ContractManagementCategory.SINGLE_DELIVERY,
        "Entrega única de solução tecnológica",
    ),
)

CATEGORY_PACKS = {
    ContractManagementCategory.SYSTEM: "TIC",
    ContractManagementCategory.EQUIPMENT: "BENS_EQUIPAMENTOS",
    ContractManagementCategory.CONTINUOUS_SERVICE: "SERVICOS_CONTINUADOS",
    ContractManagementCategory.SINGLE_DELIVERY: "ENTREGA_UNICA",
}


def seed_contract_governance(*, contract, actor, category):
    """Cria exemplos fictícios de governança sem duplicar registros em reexecuções."""
    today = timezone.localdate()
    created = 0

    if not ContractAlertPolicy.objects.filter(contract=contract).exists():
        update_alert_policy(
            contract_id=contract.pk,
            actor=actor,
            days=[120, 90, 60, 30, 15],
        )
        created += 1

    obligation_title = f"{GOVERNANCE_MARKER} Conferência documental mensal"
    if not ContractObligation.objects.filter(
        contract=contract, title=obligation_title,
    ).exists():
        create_obligation(
            contract_id=contract.pk,
            actor=actor,
            data={
                "title": obligation_title,
                "category": ContractObligationCategory.DOCUMENTARY,
                "due_date": today - timedelta(days=3),
                "responsible": "Equipe fictícia de fiscalização",
                "source_reference": f"{GOVERNANCE_MARKER} Fonte fictícia para demonstração.",
                "evidence_reference": "",
                "status": ContractObligationStatus.PENDING,
                "notes": "Prazo fictício em atraso para demonstrar o painel de alertas.",
            },
        )
        created += 1

    if not ContractChange.objects.filter(
        contract=contract,
        change_type=ContractChangeType.APOSTILLE,
        number="DEMO-AP-01",
    ).exists():
        create_contract_change(
            contract_id=contract.pk,
            actor=actor,
            data={
                "change_type": ContractChangeType.APOSTILLE,
                "number": "DEMO-AP-01",
                "official_date": today - timedelta(days=30),
                "effective_date": today - timedelta(days=25),
                "value_delta": Decimal("25000.00"),
                "validity_end_after": contract.validity_end + timedelta(days=30),
                "source_reference": f"{GOVERNANCE_MARKER} Instrumento exclusivamente fictício.",
                "summary": "Exemplo fictício de atualização do valor e da vigência.",
                "status": ContractChangeStatus.EFFECTIVE,
                "void_reason": "",
            },
        )
        created += 1

    receipt_reference = f"{GOVERNANCE_MARKER} Termo provisório"
    if not ContractReceipt.objects.filter(
        contract=contract, term_reference=receipt_reference,
    ).exists():
        create_receipt(
            contract_id=contract.pk,
            actor=actor,
            data={
                "receipt_type": ContractReceiptType.PROVISIONAL,
                "receipt_date": today - timedelta(days=10),
                "result": ContractReceiptResult.ACCEPTED,
                "object_reference": "Entrega fictícia da demonstração",
                "term_reference": receipt_reference,
                "reservations": "",
            },
        )
        created += 1

    risk_title = f"{GOVERNANCE_MARKER} Atraso na entrega demonstrativa"
    if not ContractRisk.objects.filter(contract=contract, title=risk_title).exists():
        create_risk(
            contract_id=contract.pk,
            actor=actor,
            data={
                "title": risk_title,
                "probability": ContractRiskLevel.MEDIUM,
                "impact": ContractRiskLevel.HIGH,
                "response": "Acompanhar o cronograma fictício e registrar a cobrança demonstrativa.",
                "owner": "Fiscal fictício responsável",
                "source_reference": f"{GOVERNANCE_MARKER} Mapa de riscos fictício.",
                "review_date": today + timedelta(days=10),
                "status": ContractRiskStatus.MONITORING,
            },
        )
        created += 1

    pack_code = CATEGORY_PACKS[category]
    if not ContractChecklistItem.objects.filter(
        contract=contract, pack_code=pack_code,
    ).exists():
        _, pack_created = apply_control_pack(
            contract_id=contract.pk,
            actor=actor,
            pack_code=pack_code,
        )
        created += pack_created

    external_specs = (
        (
            ContractExternalSystem.SIAG,
            "Atualização cadastral da execução contratual",
            "",
            True,
            today + timedelta(days=5),
            ContractExternalRecordStatus.PENDING,
        ),
        (
            ContractExternalSystem.SIGADOC,
            "Tramitação do processo de fiscalização",
            f"DEMO-SIGADOC-{contract.pk}",
            True,
            None,
            ContractExternalRecordStatus.REGISTERED,
        ),
        (
            ContractExternalSystem.PNCP,
            "Publicação ou atualização contratual a confirmar",
            "",
            False,
            None,
            ContractExternalRecordStatus.PENDING,
        ),
    )
    for system, label, reference, required, due_date, status in external_specs:
        if ContractExternalRecord.objects.filter(
            contract=contract, system=system, label=label,
        ).exists():
            continue
        create_external_record(
            contract_id=contract.pk,
            actor=actor,
            data={
                "system": system,
                "label": label,
                "reference": reference,
                "required": required,
                "due_date": due_date,
                "status": status,
                "source_reference": (
                    f"{GOVERNANCE_MARKER} Controle fictício; confirmar aplicabilidade na fonte oficial."
                ),
                "notes": "Registro exclusivamente demonstrativo, sem integração externa.",
            },
        )
        created += 1
    return created


def _eligible_users():
    return User.objects.filter(
        status=AccountStatus.ACTIVE,
        is_active=True,
        archived_at__isnull=True,
        profile__in=(
            UserProfile.ADMINISTRATOR_GENERAL,
            UserProfile.FISCAL_TITULAR,
            UserProfile.AUXILIARY_ADMINISTRATIVE,
            UserProfile.ADMINISTRATIVE_MANAGER,
            UserProfile.CONTRACT_MANAGER,
        ),
    )


class Command(BaseCommand):
    help = (
        "Cria contratos e dados fictícios idempotentes para todas as contas "
        "ativas dos cinco perfis da demonstração."
    )

    def handle(self, *args, **options):
        if getattr(settings, "APP_ENVIRONMENT", "") != "demo":
            raise CommandError("Operação recusada: comando exclusivo do ambiente demo.")
        email = os.getenv("DEMO_SWITCH_CONTROLLER_EMAIL", "").strip()
        if not email:
            raise CommandError("Defina DEMO_SWITCH_CONTROLLER_EMAIL.")

        switch = (
            DemoProfileSwitch.objects.select_related("controller")
            .prefetch_related("targets__user")
            .filter(controller__email__iexact=User.objects.normalize_login_email(email))
            .first()
        )
        if switch is None or switch.targets.count() != 5:
            raise CommandError("Habilite primeiro a troca entre os cinco perfis.")

        fiscal_target = switch.targets.filter(
            profile=UserProfile.FISCAL_TITULAR
        ).select_related("user").first()
        if fiscal_target is None:
            raise CommandError("A troca multiperfil não possui Fiscal Titular.")

        fiscals = list(
            _eligible_users()
            .filter(profile__in=FISCAL_TITULAR_PROFILES)
            .select_related("organization")
            .order_by("pk")
        )
        invalid_fiscals = [
            fiscal.email
            for fiscal in fiscals
            if not fiscal.organization_id or not fiscal.organization.is_active
        ]
        if invalid_fiscals:
            raise CommandError(
                "Existem Fiscais ativos sem organização ativa; regularize antes da carga: "
                + ", ".join(invalid_fiscals)
            )

        with transaction.atomic():
            contracts, created_contracts, seeded_contracts, governance_records = self._seed_contracts(
                fiscals=fiscals,
                primary_fiscal_id=fiscal_target.user_id,
            )
            linked_managers = self._link_contract_managers(contracts)
            self._validate_visibility()

        self.stdout.write(
            self.style.SUCCESS(
                "Carteira fictícia pronta: "
                f"{len(contracts)} contrato(s), {created_contracts} novo(s), "
                f"{seeded_contracts} pacote(s) operacional(is) criado(s) e "
                f"{governance_records} registro(s) de governança criado(s); "
                f"{linked_managers} Gestor(es) do Contrato vinculado(s)."
            )
        )

    def _seed_contracts(self, *, fiscals, primary_fiscal_id):
        today = timezone.localdate()
        contracts = []
        created_contracts = 0
        seeded_contracts = 0
        governance_records = 0
        for fiscal in fiscals:
            slots = len(CATEGORIES) if fiscal.pk == primary_fiscal_id else 1
            for index in range(slots):
                category, object_text = CATEGORIES[index % len(CATEGORIES)]
                number = f"DEMO-{fiscal.pk:04d}-{index + 1:02d}/2026"
                contract = Contract.objects.filter(
                    number=number,
                    responsible_fiscal=fiscal,
                ).first()
                if contract is not None and PORTFOLIO_MARKER not in contract.notes:
                    raise CommandError(
                        f"O número {number} já existe sem a marca da carteira fictícia."
                    )
                if contract is None:
                    contract = create_contract(
                        actor=fiscal,
                        number=number,
                        process_number=f"DEMO-PROC-{fiscal.pk:04d}-{index + 1:02d}",
                        object=f"{object_text} — dado exclusivamente fictício",
                        supplier_name="Fornecedor Fictício de Demonstração Ltda.",
                        supplier_tax_id="12345678000199",
                        signature_date=today - timedelta(days=90),
                        validity_start=today - timedelta(days=90),
                        validity_end=today + timedelta(days=730),
                        original_value=Decimal("500000.00")
                        + (Decimal("25000.00") * index),
                        notes=f"{PORTFOLIO_MARKER} {MARKER} Uso exclusivo em demonstração.",
                    )
                    created_contracts += 1
                if seed_contract_presentation(contract=contract, actor=fiscal):
                    seeded_contracts += 1
                classification = ContractClassification.objects.filter(
                    contract=contract,
                    status=IntelligenceReviewStatus.CONFIRMED,
                    management_category=category,
                ).first()
                if classification is None:
                    result = run_contract_intelligence(
                        contract_id=contract.pk,
                        actor=fiscal,
                    )
                    confirm_contract_classification(
                        contract_id=contract.pk,
                        actor=fiscal,
                        modality=result.modality,
                        management_category=category,
                    )
                governance_records += seed_contract_governance(
                    contract=contract,
                    actor=fiscal,
                    category=category,
                )
                contracts.append(contract)
        return contracts, created_contracts, seeded_contracts, governance_records

    def _link_contract_managers(self, contracts):
        managers = list(
            _eligible_users()
            .filter(profile=UserProfile.CONTRACT_MANAGER)
            .order_by("pk")
        )
        for index, manager in enumerate(managers):
            # Dois vínculos demonstram o seletor sem transformar este perfil
            # em uma visão geral irrestrita da carteira.
            for offset in range(min(2, len(contracts))):
                contract = contracts[(index + offset) % len(contracts)]
                existing = ContractAccess.objects.filter(
                    contract=contract,
                    user=manager,
                ).first()
                if existing and existing.status == ContractAccessStatus.ACTIVE:
                    continue
                share_contract_read_only(
                    contract_id=contract.pk,
                    actor=contract.responsible_fiscal,
                    email=manager.email,
                    confirm_regrant=existing is not None,
                )
        return len(managers)

    def _validate_visibility(self):
        missing = []
        for user in _eligible_users().select_related("organization"):
            if not contracts_visible_to(user).exists():
                missing.append(user.email)
        if missing:
            raise CommandError(
                "A carteira fictícia não ficou visível para todas as contas aptas: "
                + ", ".join(missing)
            )
