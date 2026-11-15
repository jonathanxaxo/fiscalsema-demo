# Sprint 39 — NF ligada aos serviços, valor dimensionado e devolução da NF

Referência: FiscalSema Light (ADR 0022), somente lido e reescrito no Demo.

## Autorização

Parte final de "Catálogo, ciclo e NF", com execução em sequência autorizada.

## Incluído

- A NF pode indicar os **serviços que cobra**: só serviços **homologados** e
  ainda não cobrados em outra NF ativa.
- **Valor dimensionado** = Σ UST/HST/USN dos serviços × valor unitário da OS;
  a tela da NF mostra valor da NF × dimensionado e a diferença.
- **Devolver para correção**: data (não futura, não anterior à emissão) e
  motivo obrigatórios; NF com pagamento não pode ser devolvida.
- **NF devolvida sai de todos os cálculos**: posição financeira, saldo
  faturável da OS, conferência, duplicidade, painel, dashboard executivo,
  prestação de contas e relatórios; fica somente leitura, não recebe pagamento
  e continua no histórico.
- **NF corrigida** informa qual devolvida **substitui** (mesma OS, uma única
  substituição) e pode cobrar os mesmos serviços.
- Avisos no sino e no painel: NF com valor diferente do dimensionado, NF
  devolvida aguardando a corrigida, serviço aceito sem Termo e serviço
  homologado sem NF.
- Na OS, cada serviço homologado mostra "Faturada", "Paga parcialmente" ou "Paga".

## Migração

`contracts/0023_nf_servicos_devolucao`: acrescenta campos opcionais à NF e a
tabela NF↔serviços; nenhum registro existente é alterado (NF antigas continuam
ativas e sem comparação).
