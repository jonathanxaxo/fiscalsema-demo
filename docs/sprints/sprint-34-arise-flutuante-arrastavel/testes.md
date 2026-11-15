# Testes — Sprint 34 (2026-11-15)

| Verificação (Playwright) | Resultado |
|---|---|
| Arrastar o botão para outro ponto, sem abrir o chat | moveu; não abriu |
| Clique abre a janela ao lado do botão, dentro da tela | sim |
| Arrastar a janela pelo cabeçalho | moveu |
| Minimizar e reabrir | conversa mantida; mesma posição |
| Fechar e reabrir | conversa nova |
| Outra página | botão no mesmo lugar |
| Celular (iPhone 13) | abre em tela cheia |
| `python scripts/security/scan_repository.py` | PASS |
| `python manage.py test --settings=core.settings_test --noinput` | 632 testes OK |

Erro encontrado e corrigido durante o teste: o movimento rápido do mouse saía
do botão e o arraste parava; passou a ser acompanhado pela janela inteira.
