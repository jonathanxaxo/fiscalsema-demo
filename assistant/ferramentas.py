"""Consultas futuras do Assistente IA (preparadas e DESLIGADAS na Sprint 21).

Quando forem autorizadas em sprint própria, as consultas a contratos, OS,
empenhos, prazos, pagamentos e relatórios deverão:

- passar somente pelos serviços internos (ex.: ``contracts_visible_to``,
  ``build_contract_dashboard``), nunca por SQL nem acesso direto da IA ao banco;
- respeitar o perfil ativo e as permissões do usuário;
- devolver texto resumido para o bloco ``<dados>`` do prompt
  (limite ``prompt.MAX_DATA_CHARS``);
- ser somente leitura.
"""

ENABLED = False


def authorized_data(user, *, route="", contract_id=None):
    """Texto de dados autorizados para o prompt. Desligado nesta versão."""
    return ""
