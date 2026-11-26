"""Resolução segura do contrato ativo usado pelo Assistente Arise."""

from dataclasses import dataclass

from contracts.services import contracts_visible_to


QUERY_CONTRACT_VIEWS = {
    "home",
    "contracts:executive_dashboard",
    "contracts:administrative_portfolio_report",
    "assistant:chat",
    "assistant:conversation",
}
CONTRACT_PK_VIEWS = {
    "contracts:detail",
    "contracts:dashboard",
    "contracts:update",
}


class InvalidContractContext(ValueError):
    """O identificador recebido não representa um contrato."""


class UnavailableContractContext(LookupError):
    """O contrato não existe no escopo autorizado da pessoa."""


@dataclass(frozen=True)
class ContractContext:
    contract: object | None = None
    requested: bool = False
    state: str = "none"

    @property
    def contract_id(self):
        return self.contract.pk if self.contract is not None else None

    @property
    def key(self):
        return str(self.contract_id) if self.contract_id is not None else "geral"

    @property
    def prompt_text(self):
        if self.contract is not None:
            return (
                "Contrato ativo validado pelo backend: "
                f"{self.contract.number} — {self.contract.object[:120]}. "
                "Este é o único contrato específico que pode ser considerado nesta pergunta."
            )
        if self.state == "unavailable":
            return (
                "O contrato solicitado não está disponível no escopo autorizado atual. "
                "Não use valores de contratos mencionados no histórico."
            )
        return (
            "Nenhum contrato específico está selecionado. Use somente o escopo geral "
            "permitido ao perfil e informe essa condição quando a pergunta exigir um contrato."
        )

    def template_values(self):
        return {
            "assistant_contract": self.contract,
            "assistant_contract_id": self.contract_id or "",
            "assistant_contract_state": self.state,
            "assistant_contract_context_key": self.key,
        }


def unavailable_context():
    return ContractContext(requested=True, state="unavailable")


def _parse_contract_id(raw_value):
    if raw_value is None or str(raw_value).strip() == "":
        return None
    value = str(raw_value).strip()
    if not value.isdecimal():
        raise InvalidContractContext("Contrato ativo inválido.")
    return int(value)


def resolve_contract_context(user, raw_value, *, requested=None):
    """Resolve o identificador exclusivamente no queryset autorizado do usuário."""
    contract_id = _parse_contract_id(raw_value)
    was_requested = bool(contract_id is not None) if requested is None else requested
    if contract_id is None:
        return ContractContext(requested=was_requested)
    contract = contracts_visible_to(user).filter(pk=contract_id).first()
    if contract is None:
        raise UnavailableContractContext(
            "O contrato ativo está indisponível ou fora do seu escopo autorizado."
        )
    return ContractContext(contract=contract, requested=True, state="selected")


def request_contract_candidate(request):
    """Obtém somente candidatos de rotas e filtros que representam contratos."""
    resolver = getattr(request, "resolver_match", None)
    if resolver is None:
        return None, False
    kwargs = resolver.kwargs or {}
    if "contract_pk" in kwargs:
        return kwargs["contract_pk"], True
    if resolver.view_name in CONTRACT_PK_VIEWS and "pk" in kwargs:
        return kwargs["pk"], True
    if resolver.view_name in QUERY_CONTRACT_VIEWS and "contract" in request.GET:
        return request.GET.get("contract"), True
    return None, False


def resolve_request_contract(request, *, strict=False):
    raw_value, requested = request_contract_candidate(request)
    try:
        return resolve_contract_context(
            request.user, raw_value, requested=requested
        )
    except (InvalidContractContext, UnavailableContractContext):
        if strict:
            raise
        return unavailable_context()
