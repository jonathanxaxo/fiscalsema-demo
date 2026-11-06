# Diagnóstico visual (Sprint 04)

Telas capturadas com dados fictícios em 1366×800 (computador) e iPhone 13
(celular). Capturas selecionadas em `capturas-antes/`.

## Visão geral

A base visual já é organizada (paleta verde, menu lateral, cartões, foco de
teclado, aviso de demonstração). O trabalho recomendado é **lapidar e
padronizar**, não refazer.

## Problemas encontrados

### Prioridade alta (afetam leitura ou funcionamento)

| # | Problema | Onde | Evidência |
|---|---|---|---|
| A1 | Palavras, datas e valores quebram no meio ("especializ/ado", "31/10/202/6", "OS-/001", "R$/480.00") por causa de `overflow-wrap: anywhere` nas células de tabela | todas as tabelas, pior no celular | `05-itens-desktop.png`, `06-os-desktop.png`, `02-contratos-celular.png` |
| A2 | Ano do empenho exibido com separador de milhar ("2.026") | Painel → Posição dos empenhos (`templates/home.html`) | `01-painel-desktop.png` |
| A3 | No celular, as tabelas cortam colunas à direita sem indicar que há rolagem; ações da linha ficam escondidas | listas no celular | `02-contratos-celular.png` |
| A4 | Texto interno de desenvolvimento visível ao usuário: "rateios da Etapa 19" | Detalhe do contrato (`templates/contracts/contract_detail.html`) | `03-contrato-detalhe-desktop.png` |

### Prioridade média (consistência e identidade)

| # | Problema | Onde |
|---|---|---|
| M1 | Sem logotipo: marca é o texto "FS" em um quadrado; topo mostra "FiscalSema Light" | topo e login |
| M2 | Sem favicon (ícone da aba do navegador) | todas |
| M3 | Ícones do menu são caracteres de texto (⌂ ▣ ✦ ♙ ⌘) que variam por sistema operacional | menu lateral |
| M4 | Páginas de lista internas (Itens, OS, Empenhos) não seguem o padrão da lista de Contratos: sem rótulo superior, sem descrição, "Cadastrar" como link simples em vez de botão, status em texto puro em vez de etiqueta colorida | `05-itens`, `06-os`, `08-empenhos` |
| M5 | Faixa de demonstração em marrom-avermelhado destoa da paleta (deve continuar chamativa, pois é obrigatória) | todas |
| M6 | Quantidades com 4 casas decimais ("20,0000 Hora", "1.200,0000") | Itens e OS |
| M7 | CNPJ sem máscara ("12345678000199") | Detalhe do contrato |

### Prioridade baixa (usabilidade)

| # | Problema | Onde |
|---|---|---|
| B1 | Painel muito longo (≈3.900 px); alertas importantes ("Central de trabalho", "Prazos de OS vencidos") aparecem no fim | Painel |
| B2 | No detalhe do contrato, os botões de ação ficam no fim da página, após ~25 linhas de dados | Detalhe do contrato |
| B3 | Formulário de cadastro em coluna única e longa; campos curtos (datas, valores) poderiam ficar lado a lado | Cadastrar contrato |

## Observação

Os campos de data aparecem como "mm/dd/yyyy" nas capturas porque o navegador
de teste estava em inglês; em navegador em português aparecem "dd/mm/aaaa".
Não é defeito do sistema.

## Proposta de divisão (sujeita à autorização)

- **Sprint 05 — Identidade visual:** M1, M2, M3, M5.
- **Sprint 06 — Correções de leitura:** A1, A2, A3, A4, M6, M7.
- **Sprint 07 — Padronização das telas:** M4, B2, B3.
- **Sprint 08 — Painel:** B1 (exige decisão sobre a ordem das seções).

Itens que mudam regras ou textos de negócio (A4, M6, M7, B1) precisam de
confirmação antes de implementar.
