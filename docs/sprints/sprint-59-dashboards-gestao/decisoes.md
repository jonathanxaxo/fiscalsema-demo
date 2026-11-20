# Decisões — Sprint 59

1. “Em atraso” significa OS nos estados Aberta, Assinada, Em execução ou
   Suspensa cujo prazo contratual informado é anterior à data atual.
2. Prazo da fábrica continua sendo um alerta de cobrança separado e não é
   confundido com atraso contratual.
3. A Auxiliar recebe somente os campos necessários ao acompanhamento: número
   da OS, contrato, situação, datas, horas ou quantidade, valor unitário, valor
   total e situação do prazo. Não há link para conteúdo operacional ou privado.
4. O Gestor Administrativo possui visão geral de todos os contratos não
   arquivados e seletor individual. Não foi criado filtro por setor porque o
   escopo geral foi confirmado pelo responsável.
5. O Gestor do Contrato pode acumular vários vínculos, mas continua vendo
   apenas os contratos concedidos individualmente em `READ_ONLY`.
6. Relatório gerencial é consulta de demonstração: não constitui atesto,
   homologação, liquidação, autorização ou recomendação de pagamento.
7. Os painéis reutilizam `contracts_visible_to`, `contracts_exportable_by` e
   `work_orders_visible_to`; filtros de interface nunca concedem acesso.
8. Contratos arquivados permanecem excluídos pelo backend. Seleções fora do
   escopo retornam `404`, e perfil sem competência recebe `403` no relatório.
9. A carga fictícia cria no máximo dois vínculos distintos por Gestor do
   Contrato, preservando idempotência e sem transformar o perfil em carteira
   irrestrita.
