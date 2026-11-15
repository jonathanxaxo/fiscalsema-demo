# Sprint 35 — Formatação, CPF/CNPJ e comportamentos de tela (referência: FiscalSema Light)

## Pedido do responsável

"Verifique o visual, as fórmulas e a funcionalidade que não tem no FiscalSema
Demo olhando no GitHub do FiscalSema Light; não altere nada lá, apenas pegue
informações e coloque as melhores coisas no nosso sistema. Não misture os
sistemas." Escolhidos por clique: visual/formatação/CNPJ, prazos da OS,
dashboard executivo e catálogo/ciclo/NF, todos em sequência (Sprints 35 a 38).

## Método

- Repositório do Light somente lido: versão 2026.11.14.2 exportada para uma
  pasta temporária, comparada arquivo a arquivo e executada localmente com
  dados fictícios próprios para comparar telas lado a lado. Nada foi enviado ao
  Light.
- Nada copiado inteiro: cada recurso foi reescrito no código e nas regras do
  Demo, mantendo a identidade visual do Demo (logo, ícones, faixa de
  demonstração).

## Incluído

- CPF/CNPJ aceito com ou sem pontuação no contrato e na NF; o sistema guarda
  só os dígitos, recusa tamanho diferente de 11/14 e mostra o valor formatado
  ao editar.
- Máscara de CPF/CNPJ enquanto digita.
- Barras de progresso limitadas a 0–100% (filtro `barra`): o texto continua
  mostrando o percentual real, mas a barra não estoura a caixa.
- Links internos (`#seção`) abrem a parte recolhida correspondente.
- Painel: trocar o contrato no seletor já atualiza a tela (o botão continua).

## Já existia no Demo (não duplicado)

- Exibição formatada de CPF/CNPJ (`cnpj_cpf`) e de quantidades (`quantidade`).
- Aviso ao sair de formulário alterado e bloqueio de duplo envio.
