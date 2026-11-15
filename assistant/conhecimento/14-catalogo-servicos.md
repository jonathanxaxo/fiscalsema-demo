---
titulo: Catálogo de serviços, memória de cálculo e homologação do serviço
rotas: contracts:service_catalog contracts:service_catalog_create contracts:service_catalog_update contracts:work_order_service_create contracts:work_order_service_update contracts:work_order_service_remove contracts:work_order_service_action contracts:work_order_service_homologate_accepted
perfis: FISCAL USUARIO_CONSULTA
palavras: catalogo servico servicos ust hst usn peso pesos complexidade baixa media alta memoria calculo entregue entrega aceito aceitar recusar recusa homologar homologado homologacao termo
---
**Catálogo**: Contrato → "Catálogo de serviços" → "Cadastrar serviço". Informe código, serviço, unidade de medida (ex.: por funcionalidade), peso em UST/HST/USN por complexidade (baixa, média, alta; deixe em branco quando o catálogo indicar N/A) e a fonte. Serviço inativo não entra em novas OS.
**Memória de cálculo da OS** (OS medida em quantidade, item em UST, HST, USN ou outra unidade — não vale para OS em horas): abra a OS → "Incluir serviço" → escolha serviço, complexidade e quantidade.
- Unidades da linha = quantidade × peso (o peso fica congelado na OS).
- A quantidade da OS passa a ser a soma das linhas e o valor = soma × valor unitário; as validações de saldo continuam valendo.
**Caminho de cada serviço** (botões na OS): Em andamento → **Registrar entrega** → **Aceitar** (ou **Recusar**, que volta para ajuste com motivo) → **Homologar** (informe o número do Termo de Homologação). Há "Homologar todos os aceitos" com um único termo. Só serviço em andamento pode ser editado ou removido.
Homologar é registro de ato humano; a IA nunca homologa.
