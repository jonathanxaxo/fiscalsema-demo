# Sprint 19 — Acompanhamento mensal de OS

## Solicitação

Trazer do sistema principal o acompanhamento mensal de Ordens de Serviço, para
o fiscal saber, a cada mês, quais OS contínuas ainda não foram atualizadas.

## Decisões do responsável (por clique)

- o aviso aparece no **painel e no sino** (o verde, "pago no mês", não vai ao sino);
- **nenhuma OS fictícia é marcada automaticamente**: o responsável marca na tela
  depois da migração.

## Regra (igual ao sistema principal)

Entram as OS **abertas** (aberta, assinada, em execução, suspensa) que:

- têm a caixinha "Exige acompanhamento mensal" marcada; ou
- usam item cuja unidade contratual é "Mês" (automático).

Situação na competência do mês atual (MM/AAAA, comparada com a competência
cadastrada nos registros):

| Situação | Cor |
|---|---|
| OS suspensa; conferir providência e vigência | amarelo |
| Pagamento registrado para a competência | verde |
| NF cadastrada; conferir Atesto, RAER, homologação e pagamento | amarelo |
| Execução atualizada; aguardando NF e conferência documental | amarelo |
| Atualização da competência pendente | vermelho |

O aviso não autoriza pagamento e não substitui Atesto, RAER ou Termo de
Homologação.

## Fora do escopo

API v1/MCP (o campo não foi exposto), workflow para marcar OS fictícias.
