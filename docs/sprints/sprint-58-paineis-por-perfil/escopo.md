# Sprint 58 — Painéis independentes por perfil

## História de usuário

- **COMO:** responsável pela demonstração do FiscalSema;
- **QUERO:** alternar a conta controladora entre os cinco perfis e encontrar
  um painel próprio, com dados e objetivos adequados a cada função;
- **PARA:** demonstrar responsabilidades reais sem padronizar ou unificar as
  visões do sistema.

## Entregas

- Administrador Geral permanece no painel central de acessos;
- Fiscal Titular permanece no painel operacional do contrato;
- Auxiliar Administrativa recebe painel exclusivo de metadados e pendências
  cadastrais, sem contratos arquivados, valores ou arquivos privados; o sino
  exibe apenas alertas administrativos seguros;
- Gestor Administrativo recebe painel consolidado por classificação, valores,
  empenhos, pagamentos, saldos e seleção individual;
- Gestor do Contrato recebe painel somente leitura dos vínculos individuais,
  com indicadores, gráfico, dashboard completo e emissão de relatório;
- troca multiperfil carrega o template e os dados do perfil selecionado;
- regras de autorização continuam no backend e não são ampliadas pela tela.

## Fora do escopo

- alterar modelos, migrations, senhas ou vínculos de acesso;
- unificar os painéis em uma única visualização configurável;
- permitir que a Auxiliar abra arquivos privados ou contratos arquivados;
- conceder escrita ao Gestor do Contrato ou ao Gestor Administrativo;
- merge e deploy sem autorização específica após a revisão do PR.
