# Testes — Sprint 71

## Critérios automatizados

- contrato escolhido no painel, em rota contratual e na tela cheia;
- seleção padrão do painel e estado explícito sem seleção;
- dados enviados ao modelo limitados ao contrato ativo;
- troca A → B cria conversa isolada e não reaproveita mensagens;
- permanência no mesmo contrato mantém o histórico;
- identificador inválido, contrato não autorizado e arquivado são recusados
  antes do provedor;
- contrato sem OS ou empenho permanece consultável;
- conversa salva restaura o contexto autorizado;
- revogação de acesso oculta a conversa contratual anteriormente salva;
- outra sessão/perfil não reaproveita conversa anterior;
- marcação do navegador carrega o contexto e o mecanismo de reset.

## Execução local

Data: 26/11/2026.

- primeira execução de regressão: **13 falhas esperadas**, comprovando que os
  cenários detectavam a ausência do recurso;
- após a implementação e a revisão: **17 testes específicos aprovados** em
  1,624 segundo;
- provedor de IA simulado, chave exclusivamente fictícia e PostgreSQL 17
  temporário e isolado;
- suíte Django integral final: **812 testes aprovados** em 103,931 segundos;
- configuração Django: aprovada, sem alertas;
- migrations: aprovadas, nenhuma alteração adicional detectada;
- scanner do repositório: aprovado, sem segredo, dado real ou artefato
  proibido;
- adaptador MCP: **6 testes aprovados**;
- sintaxe do JavaScript e `git diff --check`: aprovados.

Uma execução agrupada das verificações terminou antes da suíte ao inicializar
o comando de migrations. A repetição isolada de `check` e `makemigrations`,
com a mesma configuração descartável, foi aprovada; tratou-se de falha da
orquestração do comando combinado, não de defeito do sistema.

Nenhum dado real, senha, serviço de IA externo ou banco institucional foi
acessado.

## Publicação

- PR #70: CI `django-postgresql` aprovada; merge em 26/11/2026 (commit `1334ed1`).
- Migração manual do banco da demo (fluxo "Migracao manual do FiscalSema Demo",
  execução 14) concluída com sucesso, aplicando `assistant.0002`.
- Vercel: deploy de produção `READY` para o commit `1334ed1`.
- Conferência em produção: `/healthz` com banco "ok" e nenhum erro de execução
  nos 30 minutos seguintes.
