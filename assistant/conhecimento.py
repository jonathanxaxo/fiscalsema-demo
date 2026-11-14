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


@dataclass(frozen=True)
class Section:
    name: str
    title: str
    routes: frozenset
    profiles: frozenset
    keywords: frozenset
    body: str

    def visible_to(self, profile):
        return "todos" in self.profiles or profile in self.profiles


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


def suggestions_for(profile):
    return SUGGESTIONS.get(profile, SUGGESTIONS["FISCAL"])
