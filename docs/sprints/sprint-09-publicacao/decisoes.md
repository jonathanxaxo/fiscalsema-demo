# Decisões da Sprint 09

1. **Preview com "Bad Request (400)" no apelido da branch:** `core/settings_demo.py`
   inclui automaticamente em `ALLOWED_HOSTS` somente `VERCEL_URL`, que é o
   endereço único de cada deploy. O apelido da branch não é aceito, por
   segurança. Para conferir um Preview, usar o endereço único (sem `-git-`),
   listado em "Domains" na página do deploy na Vercel.
2. Aceitar também o apelido da branch (`VERCEL_BRANCH_URL`) altera regra de
   segurança e fica como proposta para sprint própria, mediante autorização.
3. O merge foi executado pelo agente a pedido explícito do responsável, após
   CI verde. A conferência da produção é humana.
4. URLs completas da Vercel não foram registradas porque contêm identificador
   pessoal; a auditoria `scripts/security/scan_repository.py` as rejeitaria.

5. **Sprint 10 descartada:** foi implementado um fluxo para redefinir a senha
   do administrador (comando, workflow manual e 7 testes; 431 testes
   aprovados), mas o responsável informou que conhece a senha. Por não ser
   necessária, a entrega foi desfeita com `git revert` (commits `37397f1` e
   reversão seguinte) e não chega à `main`. Se voltar a ser necessária, pode
   ser recuperada desses commits em nova sprint.

## Pendências levadas adiante

- e-mails de recuperação de senha ainda citam "FiscalSema Light";
- confirmar cores de status das OS;
- avaliar suporte a `VERCEL_BRANCH_URL` no Preview.
