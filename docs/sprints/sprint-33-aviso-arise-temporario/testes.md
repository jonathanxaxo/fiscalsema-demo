# Testes — Sprint 33 (2026-11-15)

| Verificação | Resultado |
|---|---|
| Navegador (Playwright, relógio simulado): visível ao abrir | sim |
| Aos 34 s | visível |
| Aos 35,5 s | oculto |
| Fechar e reabrir | visível de novo; some após 35 s |
| `python scripts/security/scan_repository.py` | PASS |
| `python manage.py test --settings=core.settings_test --noinput` | 631 testes OK |
