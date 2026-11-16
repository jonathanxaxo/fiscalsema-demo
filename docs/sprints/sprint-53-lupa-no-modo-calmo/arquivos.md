# Arquivos — Sprint 53

- `core/static/core/img/logo.svg`: remove o bloqueio interno que congelava a lupa no modo Calmo.
- `templates/accounts/base.html`: informa a versão estática como dado do logotipo, sem troca automática pelo sistema operacional.
- `core/static/core/js/app.js`: usa a versão estática somente quando a pessoa escolhe `Sem`.
- `core/static/core/css/app.css`: remove o bloqueio isolado do brilho do logotipo.
- `core/test_logo_escaneando.py`: protege os modos Vivo, Calmo e Sem.
- `docs/sprints/README.md`, `templates/core/metodologia.html` e esta pasta: registram a correção.
