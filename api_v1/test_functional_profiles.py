from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import AccountStatus, User, UserProfile
from contracts.models import (
    Contract,
    ContractAccess,
    ContractAccessStatus,
    ContractAccessType,
    FiscalSubstitution,
    FiscalSubstitutionStatus,
)
from documents.models import Document, DocumentType, RelatedEntityType
from organizations.models import Organization

from .services import create_api_credential


PASSWORD = "SenhaMuitoForte!2026"


class FunctionalProfileApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name="Organização API A")
        cls.org_b = Organization.objects.create(name="Organização API B")
        cls.admin = User.objects.create_superuser(
            email="admin.perfis.api@example.local",
            full_name="Admin API Perfis",
            password=PASSWORD,
        )
        cls.fiscal_a = cls._user(
            "fiscal.a.api@example.local", UserProfile.FISCAL_TITULAR, cls.org_a
        )
        cls.fiscal_b = cls._user(
            "fiscal.b.api@example.local", UserProfile.FISCAL_TITULAR, cls.org_b
        )
        cls.auxiliary = cls._user(
            "auxiliar.api@example.local",
            UserProfile.AUXILIARY_ADMINISTRATIVE,
            cls.org_a,
        )
        cls.administrative_manager = cls._user(
            "gestor.adm.api@example.local",
            UserProfile.ADMINISTRATIVE_MANAGER,
            cls.org_a,
        )
        cls.contract_manager = cls._user(
            "gestor.contrato.api@example.local",
            UserProfile.CONTRACT_MANAGER,
            cls.org_a,
        )
        cls.active_substitute = cls._user(
            "substituto.ativo.api@example.local",
            UserProfile.FISCAL_TITULAR,
            cls.org_a,
        )
        cls.expired_substitute = cls._user(
            "substituto.expirado.api@example.local",
            UserProfile.FISCAL_TITULAR,
            cls.org_a,
        )
        cls.contract_a = cls._contract("API-A/2026", cls.org_a, cls.fiscal_a)
        cls.contract_b = cls._contract("API-B/2026", cls.org_b, cls.fiscal_b)
        cls.archived = cls._contract("API-ARQ/2026", cls.org_b, cls.fiscal_b)
        Contract.objects.filter(pk=cls.archived.pk).update(
            archived_at=timezone.now(),
            archived_by=cls.fiscal_b,
            archive_reason="Arquivado para teste.",
        )
        cls.manager_access = ContractAccess.objects.create(
            contract=cls.contract_a,
            user=cls.contract_manager,
            access_type=ContractAccessType.READ_ONLY,
            status=ContractAccessStatus.ACTIVE,
            granted_by=cls.fiscal_a,
        )
        today = timezone.localdate()
        FiscalSubstitution.objects.create(
            contract=cls.contract_a,
            substitute=cls.active_substitute,
            email=cls.active_substitute.email,
            starts_on=today,
            ends_on=today + timedelta(days=5),
            status=FiscalSubstitutionStatus.LINKED,
            created_by=cls.fiscal_a,
            linked_at=timezone.now(),
        )
        FiscalSubstitution.objects.create(
            contract=cls.contract_a,
            substitute=cls.expired_substitute,
            email=cls.expired_substitute.email,
            starts_on=today - timedelta(days=10),
            ends_on=today - timedelta(days=1),
            status=FiscalSubstitutionStatus.LINKED,
            created_by=cls.fiscal_a,
            linked_at=timezone.now(),
        )
        cls.document = Document.objects.bulk_create(
            [
                Document(
                    contract=cls.contract_a,
                    title="Contrato fictício",
                    document_type=DocumentType.CONTRACT,
                    origin="Teste automatizado",
                    related_entity_type=RelatedEntityType.CONTRACT,
                    file="documents/contrato-api-ficticio.pdf",
                    original_name="contrato-api-ficticio.pdf",
                    mime_type="application/pdf",
                    file_size=100,
                    sha256="b" * 64,
                    uploaded_by=cls.fiscal_a,
                )
            ]
        )[0]

    @classmethod
    def _user(cls, email, profile, organization):
        return User.objects.create_user(
            email=email,
            full_name=email.split("@")[0],
            password=PASSWORD,
            profile=profile,
            status=AccountStatus.ACTIVE,
            organization=organization,
        )

    @classmethod
    def _contract(cls, number, organization, fiscal):
        return Contract.objects.create(
            number=number,
            process_number=f"PROC-{number}",
            object="Contrato fictício para teste da API",
            contracting_organization=organization,
            supplier_name="Fornecedor Fictício",
            supplier_tax_id="12345678000199",
            signature_date=date(2026, 1, 1),
            validity_start=date(2026, 1, 1),
            validity_end=date(2027, 12, 31),
            original_value=Decimal("1000.00"),
            responsible_fiscal=fiscal,
        )

    def token_for(self, user):
        _credential, token = create_api_credential(
            name=f"Perfil {user.pk}", authorized_user=user, actor=self.admin
        )
        return token

    def api_get(self, path, user):
        return self.client.get(
            path, HTTP_AUTHORIZATION=f"Bearer {self.token_for(user)}"
        )

    def test_auxiliary_api_lists_all_active_contracts_but_never_archived(self):
        response = self.api_get("/api/v1/contracts/", self.auxiliary)
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()["results"]}
        self.assertEqual(ids, {self.contract_a.pk, self.contract_b.pk})
        self.assertNotIn(self.archived.pk, ids)

    def test_auxiliary_api_receives_document_metadata_without_private_content(self):
        capabilities = self.api_get("/api/v1/capabilities/", self.auxiliary)
        self.assertNotIn("documents.read", capabilities.json()["read_tools"])
        response = self.api_get(
            f"/api/v1/contracts/{self.contract_a.pk}/documents/", self.auxiliary
        )
        self.assertEqual(response.status_code, 200)
        metadata = response.json()["results"][0]
        self.assertEqual(metadata["id"], self.document.pk)
        self.assertNotIn("content_url", metadata)
        content = self.api_get(
            f"/api/v1/documents/{self.document.pk}/content/", self.auxiliary
        )
        self.assertEqual(content.status_code, 404)

    def test_auxiliary_cannot_use_controlled_draft_credential(self):
        _credential, token = create_api_credential(
            name="Auxiliar sem escrita",
            authorized_user=self.auxiliary,
            actor=self.admin,
            access_mode="CONTROLLED_DRAFT",
        )
        capabilities = self.client.get(
            "/api/v1/capabilities/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(capabilities.json()["controlled_drafts"], [])
        response = self.client.post(
            "/api/v1/drafts/",
            data={"entity_type": "CONTRATO"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_administrative_manager_api_has_institutional_active_portfolio(self):
        response = self.api_get("/api/v1/contracts/", self.administrative_manager)
        ids = {item["id"] for item in response.json()["results"]}
        self.assertEqual(ids, {self.contract_a.pk, self.contract_b.pk})

    def test_contract_manager_api_is_limited_to_active_individual_link(self):
        response = self.api_get("/api/v1/contracts/", self.contract_manager)
        self.assertEqual(
            {item["id"] for item in response.json()["results"]},
            {self.contract_a.pk},
        )
        self.assertEqual(
            self.api_get(
                f"/api/v1/contracts/{self.contract_b.pk}/", self.contract_manager
            ).status_code,
            404,
        )
        ContractAccess.objects.filter(pk=self.manager_access.pk).update(
            status=ContractAccessStatus.REVOKED,
            revoked_by=self.fiscal_a,
            revoked_at=timezone.now(),
        )
        response = self.api_get("/api/v1/contracts/", self.contract_manager)
        self.assertEqual(response.json()["results"], [])

    def test_substitution_is_dynamic_and_expires_without_global_access(self):
        active = self.api_get("/api/v1/contracts/", self.active_substitute)
        expired = self.api_get("/api/v1/contracts/", self.expired_substitute)
        self.assertEqual(
            {item["id"] for item in active.json()["results"]},
            {self.contract_a.pk},
        )
        self.assertEqual(expired.json()["results"], [])
