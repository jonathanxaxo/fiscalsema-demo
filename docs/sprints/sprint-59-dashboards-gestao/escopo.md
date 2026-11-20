# Sprint 59 — Dashboards de gestão e acompanhamento de OS

## História de usuário

- **COMO:** Auxiliar Administrativa, Gestor Administrativo ou Gestor do
  Contrato da demonstração;
- **QUERO:** consultar o painel próprio do meu perfil, selecionar o contrato
  adequado e acompanhar os indicadores autorizados;
- **PARA:** identificar OS abertas e em atraso, acompanhar a carteira geral ou
  os contratos vinculados e emitir relatórios sem ampliar permissões.

## Entregas

- Auxiliar Administrativa consulta as OS abertas de todos os contratos não
  arquivados, com filtro por contrato e situação, horas ou quantidades, valores
  e prazos;
- OS aberta com prazo contratual anterior à data atual aparece como **Em
  atraso**, inclusive no resumo e no sino de notificações;
- o painel da Auxiliar não apresenta documentos privados, descrição da OS nem
  links para abrir contrato, documento ou OS;
- Gestor Administrativo acompanha a carteira geral de contratos não
  arquivados e pode selecionar individualmente qualquer contrato disponível;
- dashboard gerencial apresenta valor atual, empenhado, comprometido,
  executado, faturado, pago, saldo, classificações e situação das OS;
- relatório gerencial consolidado ou individual pode ser impresso ou salvo em
  PDF; relatórios e CSV individuais já existentes permanecem disponíveis;
- Gestor do Contrato seleciona entre vários contratos vinculados à própria
  conta e continua em somente leitura;
- carga fictícia passa a vincular dois contratos a cada Gestor do Contrato para
  demonstrar o seletor de forma realista e idempotente.

## Fora do escopo

- acessar contrato arquivado ou documento privado pela Auxiliar;
- permitir escrita, atesto, homologação, liquidação ou pagamento aos Gestores;
- limitar o Gestor Administrativo por setor: o escopo confirmado é geral;
- criar migration, instalar dependência ou acessar dados reais;
- merge e deploy sem autorização específica após a validação.
