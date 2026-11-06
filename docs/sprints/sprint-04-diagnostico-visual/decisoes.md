# Decisões da Sprint 04

1. O diagnóstico foi feito com o sistema em execução, não apenas pela leitura
   do código, para basear as próximas sprints em evidência.
2. Dependências instaladas somente em ambiente virtual temporário, fora do
   repositório; `requirements.txt` não foi alterado.
3. Dados fictícios criados com as mesmas funções de serviço usadas pelos
   testes, em PostgreSQL local descartável.
4. Apenas 8 capturas foram versionadas (cerca de 1,7 MB) para não inchar o
   repositório; as demais ficaram somente na máquina temporária.
5. As próximas sprints manterão nomes de classes CSS e textos verificados por
   `core/test_ui_upgrade.py`.
