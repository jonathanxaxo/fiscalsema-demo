# Escopo da Sprint 14 — Sino de notificações

## Pedido

Trazer para a demonstração a opção de notificações existente no sistema
principal, escolhida pelo responsável.

## Entrega

Sino no topo de todas as telas, com contagem e painel de pendências:

- Fiscal: pendências dos contratos ativos ou suspensos (OS vencida, NF com
  divergência ou pendente, prazo de encaminhamento de NF, soma dos itens
  divergente, saldo baixo, empenho/horas baixos, OS sem rateio, OS concluída
  sem NF), cada uma com link para o registro exato.
- Usuário com acesso somente de leitura: link para o painel do contrato.
- Administrador: apenas solicitações de cadastro pendentes.
- Dentro das telas de um contrato, só aquele contrato aparece.
- Itens críticos primeiro; até 30 itens listados.
- Fecha ao clicar fora ou com Esc; no celular abre abaixo do cabeçalho.

## Adaptações em relação ao sistema principal

- sem o perfil "Gestor do contrato" (inexistente na demo): o caso equivalente
  é o acesso somente de leitura;
- sem o acompanhamento mensal de OS (recurso inexistente na demo);
- cores ajustadas à identidade da demo (verde e âmbar).

## Limites

- somente leitura: usa os cálculos já existentes do painel; nenhum dado é
  gravado; sem migration; sem bibliotecas; a "Central de trabalho" do painel
  foi mantida.
