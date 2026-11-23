# Decisões — Sprint 62

1. **Testar pelo caminho real.** A conta foi inativada pela mesma função da tela do
   Administrador (`change_user_status`). Alterar só o campo interno do Django não
   representa o uso do sistema.
2. **Sem mudar regra.** Os testes mostraram que a execução já é recusada; por isso a
   sprint só acrescenta testes e melhora a mensagem.
3. **Escopo de demonstração.** SMTP institucional e login pela rede da SEMA ficam para
   quando houver infraestrutura real.
