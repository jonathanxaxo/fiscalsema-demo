"""Falha se o repositório demo contiver segredos ou artefatos operacionais."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
FORBIDDEN_SUFFIXES = {
    ".bak", ".csv", ".db", ".doc", ".docx", ".dump", ".key", ".log",
    ".ods", ".p12", ".pdf", ".pem", ".pfx", ".sql", ".sqlite",
    ".sqlite3", ".xls", ".xlsx",
}
FORBIDDEN_PARTS = {"backups", "data", "documentos", "logs", "media", ".ssh"}
PATTERNS = {
    "chave privada": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
    "token GitHub": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "chave AWS": re.compile(r"AKIA[0-9A-Z]{16}"),
    "chave OpenAI": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "senha em URL PostgreSQL": re.compile(r"postgres(?:ql)?://[^\s:]+:[^\s@]+@"),
    "contrato operacional": re.compile(r"037/2026", re.IGNORECASE),
    "identificador pessoal": re.compile(r"jonathan(?:xaxo|duarte)?", re.IGNORECASE),
    "endereço interno": re.compile(r"172\.16\.110\.185"),
}


def candidate_files() -> list[Path]:
    try:
        output = subprocess.check_output(
            [
                "git",
                "-c",
                f"safe.directory={ROOT.as_posix()}",
                "-C",
                str(ROOT),
                "ls-files",
            ],
            text=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return [path for path in ROOT.rglob("*") if path.is_file()]
    return [ROOT / line for line in output.splitlines() if line]


def main() -> int:
    failures: list[str] = []
    for path in candidate_files():
        if path.resolve() == SELF:
            continue
        relative = path.relative_to(ROOT)
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            failures.append(f"arquivo proibido: {relative}")
            continue
        if any(part.casefold() in FORBIDDEN_PARTS for part in relative.parts):
            failures.append(f"diretório proibido: {relative}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                failures.append(f"{label}: {relative}")
    if failures:
        print("FALHA | auditoria do repositório demo")
        for failure in sorted(set(failures)):
            print(f"- {failure}")
        return 1
    print("PASS | nenhum segredo conhecido, dado real ou artefato proibido encontrado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
