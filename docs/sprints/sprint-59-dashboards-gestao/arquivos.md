# Arquivos — Sprint 59

| Grupo | Alteração |
|---|---|
| `core/profile_dashboards.py` | Dados autorizados, filtros, indicadores e gráficos dos painéis |
| `core/views.py` | Encaminhamento dos filtros de contrato e situação |
| `core/notifications.py` | Alerta seguro de OS em atraso para a Auxiliar |
| `templates/core/auxiliary_home.html` | Painel de OS abertas, horas, valores e atraso |
| `templates/core/administrative_manager_home.html` | Dashboard geral e seletor individual do Gestor Administrativo |
| `templates/core/contract_manager_home.html` | Terminologia “Em atraso” e seletor de vínculos preservado |
| `contracts/views.py`, `contracts/urls.py` | Relatório gerencial consolidado ou individual |
| `templates/contracts/administrative_portfolio_report.html` | Relatório imprimível e salvável em PDF |
| `contracts/management/commands/seed_demo_portfolio.py` | Dois vínculos fictícios por Gestor do Contrato |
| testes automatizados | Permissões, filtros, atraso, relatórios e idempotência |
| documentação e Metodologia | Escopo, decisões, testes e histórico da Sprint 59 |

Não há migration nem dependência nova.
