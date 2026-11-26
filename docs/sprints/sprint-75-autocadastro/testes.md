# Testes — Sprint 75

## Critérios automatizados (`accounts/test_autocadastro.py`, 16 testes)

- botão "Criar conta" no login; 404 e botão oculto quando desligado;
- lista de órgãos e setores ativos no formulário;
- conta Fiscal Titular ativa, sem senha, com órgão e setor, e evento de
  auditoria `autocadastro`;
- e-mail com link de uso único (`/conta/criar-senha/`) e sem senha escrita;
- órgão e setor novos criados, auditados e listados para a próxima pessoa;
- nome digitado igual a um existente reaproveita o registro, sem duplicar;
- regras de escolha: lista ou nome, setor do órgão certo e setor novo para
  órgão novo;
- órgão inativo não é reutilizado;
- somente os contratos fictícios marcados são compartilhados, em somente
  leitura, concedidos pelo fiscal, auditados, visíveis e não editáveis;
- senha criada pelo link, evento auditado, link não funciona de novo e o
  login passa a funcionar;
- repetir o cadastro antes da senha reenvia o link sem duplicar a conta;
- e-mail com conta e senha é recusado;
- limite de cadastros por conexão, campo anti-robô e falha de envio com
  reenvio.

Durante a sprint, os testes mostraram que o gerenciador de usuários exige
senha; a criação passou a seguir o padrão do cadastro pelo Google
(`set_unusable_password`).

## Comandos e resultados (26/11/2026)

```text
python scripts/security/scan_repository.py
PASS | nenhum segredo conhecido, dado real ou artefato proibido encontrado

python -m unittest scripts.test_mcp_server
Ran 6 tests — OK

python manage.py check --settings=core.settings_test
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run --settings=core.settings_test
No changes detected

python manage.py test --settings=core.settings_test --noinput --parallel 4
Ran 852 tests — OK

git diff --check
sem problemas
```

## Conferência no navegador (banco local fictício)

Fluxo completo com uma pessoa fictícia ("Visitante Demo Day"):

1. login com "Criar conta";
2. formulário com órgão e setor novos digitados;
3. "Confira seu e-mail";
4. "Criar sua senha" pelo link;
5. "Senha criada";
6. login e painel do contrato com o selo "Somente leitura", sem botão de nova
   OS e com 4 contratos fictícios em consulta.

O envio real do e-mail depende do SMTP já configurado na produção e é
conferido no Preview.
