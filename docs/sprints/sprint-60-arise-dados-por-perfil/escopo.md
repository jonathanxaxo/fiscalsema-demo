# Sprint 60 — Arise limitado aos dados de cada perfil

## História de usuário

- **COMO:** responsável pela demonstração do FiscalSema;
- **QUERO:** que o Assistente Arise entregue a cada perfil somente os dados
  que o painel desse perfil já mostra;
- **PARA:** impedir que a Auxiliar Administrativa receba saldo, empenhado ou
  pago do contrato e reduzir erros de leitura de valores pelo modelo.

## Problema encontrado

Durante a gravação do vídeo de demonstração (dados fictícios), no perfil
Auxiliar Administrativa, a pergunta "Qual é o saldo e o valor pago do contrato
DEMO-0002-01/2026?" recebeu saldo contratual e valor pago. A função
`assistant/ferramentas.py::authorized_data` enviava o
`contract_intelligence_snapshot` completo para todo perfil diferente do
Gestor Administrativo, inclusive a Auxiliar, contrariando as Sprints 54, 58
e 59. O modelo também leu o valor pago `22400` como "R$ 224.000,00".

## Entregas

- a Auxiliar recebe no bloco `<dados>` somente o conteúdo do próprio painel
  (`build_auxiliary_dashboard`): OS abertas e em atraso, situação, abertura,
  prazo, horas ou quantidade, valor unitário e valor da OS, total das OS
  abertas, número e objeto resumido dos contratos não arquivados;
- a Auxiliar não recebe valor atual, empenhado, comprometido, executado,
  faturado, pago ou saldo do contrato, itens, regras nem achados;
- os valores monetários enviados ao Arise, em todos os perfis, vão escritos
  em reais (ex.: "R$ 22.400,00"), sem recálculo;
- Fiscal Titular, Gestor do Contrato e Gestor Administrativo continuam
  recebendo o mesmo conteúdo de antes.

## Fora do escopo

- alterar os painéis, as permissões, os modelos ou as migrations;
- alterar o snapshot exibido na página de inteligência do contrato;
- instalar dependências, alterar o CI, fazer merge ou deploy.
