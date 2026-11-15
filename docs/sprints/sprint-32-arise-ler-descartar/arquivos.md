# Arquivos — Sprint 32

## Criados
- `assistant/anexos.py` — leitura em memória de PDF/DOCX e upload só em memória.
- `assistant/test_anexos.py` — 15 testes.
- `templates/assistant/_anexo.html` — clipe, nome do arquivo e aviso de LGPD.
- `docs/sprints/sprint-32-arise-ler-descartar/*`.

## Alterados
- `requirements.txt` — `pypdf==7.1.0`.
- `assistant/views.py` — leitor de upload em memória, CSRF mantido, anexo na pergunta, anotação e auditoria.
- `assistant/prompt.py` — bloco `<documento>` e regras 9 e 10.
- `assistant/static/assistant/chat.js` e `chat.css` — anexo nos dois chats.
- `templates/assistant/chat.html`, `templates/assistant/flutuante.html`.
- `templates/core/metodologia.html`, `docs/sprints/README.md`, `docs/seguranca/controles.md`.

## Fora do repositório (entregues ao responsável)
- `TR-ficticio-DEMO-2026-0042.pdf` / `.docx`
- `Contrato-ficticio-042-2026-DEMO.pdf` / `.docx`
