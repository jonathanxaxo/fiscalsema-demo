"""Base de conhecimento do Assistente Arise (Sprint 21).

Arquivos ``assistant/conhecimento/*.md`` com cabeçalho:

    ---
    titulo: ...
    rotas: nomes de rota (``*`` = todas as páginas)
    perfis: todos | FISCAL ADMINISTRADOR USUARIO_CONSULTA
    palavras: palavras-chave
    ---

Por velocidade, só as seções relevantes vão para o modelo: a visão geral,
as seções da página atual e as que combinam com a pergunta, até
``MAX_HELP_CHARS`` caracteres.
"""

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

MAX_HELP_CHARS = 6000
BASE_DIR = Path(__file__).resolve().parent / "conhecimento"
PROFILE_COMPATIBILITY = {
    "ADMINISTRADOR_GERAL": "ADMINISTRADOR",
    "FISCAL_TITULAR": "FISCAL",
    "AUXILIAR_ADMINISTRATIVA": "USUARIO_CONSULTA",
    "GESTOR_ADMINISTRATIVO": "USUARIO_CONSULTA",
    "GESTOR_DO_CONTRATO": "USUARIO_CONSULTA",
}


@dataclass(frozen=True)
class Section:
    name: str
    title: str
    routes: frozenset
    profiles: frozenset
    keywords: frozenset
    body: str

    def visible_to(self, profile):
        compatible = PROFILE_COMPATIBILITY.get(profile, profile)
        return "todos" in self.profiles or compatible in self.profiles


def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def words(text):
    return set(re.findall(r"[a-z0-9]{2,}", normalize(text)))


@lru_cache(maxsize=1)
def load_sections():
    sections = []
    for path in sorted(BASE_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        match = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
        if not match:
            continue
        meta = dict(
            (key.strip(), value.strip())
            for key, value in (line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
        )
        sections.append(
            Section(
                name=path.stem,
                title=meta.get("titulo", path.stem),
                routes=frozenset(meta.get("rotas", "").split()),
                profiles=frozenset(meta.get("perfis", "todos").split()),
                keywords=frozenset(words(meta.get("palavras", "") + " " + meta.get("titulo", ""))),
                body=match.group(2).strip(),
            )
        )
    return tuple(sections)


def select_sections(question, *, profile, route=""):
    """Seções em ordem de relevância, respeitando o perfil e o limite de tamanho."""
    asked = words(question)
    scored = []
    for section in load_sections():
        if not section.visible_to(profile):
            continue
        score = 3 * len(asked & section.keywords)
        if route and route in section.routes:
            score += 4
        if "*" in section.routes:
            score += 1
        if section.name.startswith("00-"):
            score += 100  # visão geral sempre entra primeiro
        if score:
            scored.append((score, section.name, section))
    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen, used = [], 0
    for _, _, section in scored:
        size = len(section.body) + len(section.title) + 8
        if used + size > MAX_HELP_CHARS:
            continue
        chosen.append(section)
        used += size
    return chosen


def help_text(question, *, profile, route=""):
    return "\n\n".join(
        f"## {section.title}\n{section.body}"
        for section in select_sections(question, profile=profile, route=route)
    )


SUGGESTIONS = {
    "ADMINISTRADOR_GERAL": (
        "Como aprovo uma solicitação de cadastro?",
        "Como bloqueio ou restauro um usuário?",
        "O que aparece na auditoria?",
    ),
    "FISCAL_TITULAR": (
        "Qual o saldo do contrato e como foi calculado?",
        "Quais inconsistências estão ativas?",
        "Como cadastro uma Ordem de Serviço?",
    ),
    "AUXILIAR_ADMINISTRATIVA": (
        "Quais contratos posso consultar?",
        "Quais documentos estão disponíveis?",
        "Existem pendências administrativas?",
    ),
    "GESTOR_ADMINISTRATIVO": (
        "Quais contratos estão ativos na carteira institucional?",
        "Qual a posição financeira consolidada?",
        "Quais prazos exigem atenção?",
    ),
    "GESTOR_DO_CONTRATO": (
        "Qual o saldo do contrato vinculado?",
        "Quais OS estão abertas?",
        "Existe alguma inconsistência?",
    ),
    "ADMINISTRADOR": (
        "Como aprovo uma solicitação de cadastro?",
        "Como bloqueio ou restauro um usuário?",
        "O que aparece na auditoria?",
    ),
    "USUARIO_CONSULTA": (
        "O que significa cada indicador do painel?",
        "Como imprimo o relatório do contrato?",
        "O que é empenho?",
    ),
    "FISCAL": (
        "Como cadastro uma Ordem de Serviço?",
        "Como funciona o acompanhamento mensal de OS?",
        "Como registro o pagamento de uma Nota Fiscal?",
    ),
}


# Sprint 74: perguntas sobre o contrato ativo. Só aparecem quando há contrato
# validado no backend; a Auxiliar não vê valores, então recebe perguntas de prazo.
_CONTRATO_FINANCEIRO = (
    "Qual é o saldo deste contrato?",
    "Quais ordens de serviço estão abertas ou vencidas?",
    "Existem notas fiscais pendentes?",
    "Quais empenhos estão associados?",
)
CONTRACT_SUGGESTIONS = {
    "FISCAL_TITULAR": _CONTRATO_FINANCEIRO,
    "FISCAL": _CONTRATO_FINANCEIRO,
    "GESTOR_DO_CONTRATO": _CONTRATO_FINANCEIRO,
    "GESTOR_ADMINISTRATIVO": _CONTRATO_FINANCEIRO,
    "USUARIO_CONSULTA": _CONTRATO_FINANCEIRO,
    "AUXILIAR_ADMINISTRATIVA": (
        "Quais ordens de serviço deste contrato estão abertas?",
        "Existem OS vencidas neste contrato?",
        "Quais prazos deste contrato exigem atenção?",
    ),
}


def suggestions_for(profile, *, contract=None):
    if contract is not None and profile in CONTRACT_SUGGESTIONS:
        return CONTRACT_SUGGESTIONS[profile]
    return SUGGESTIONS.get(profile, SUGGESTIONS["FISCAL_TITULAR"])


def contract_suggestions_for(profile):
    """Sugestões usadas quando o painel já tem um contrato ativo validado."""
    return CONTRACT_SUGGESTIONS.get(profile, suggestions_for(profile))
