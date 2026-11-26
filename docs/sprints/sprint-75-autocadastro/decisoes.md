# Decisões — Sprint 75

1. **Sem migração.** A conta usa os campos que já existem: `organization`,
   `sector`, `status=ATIVO` e senha inutilizável. A auditoria usa o evento
   `CADASTRO_SOLICITADO` com `autocadastro: true`, e a criação da senha usa
   `SENHA_ALTERADA` com `origem: autocadastro`.
2. **Posse do e-mail.** A conta só pode ser usada depois que a pessoa cria a
   senha pelo link de uso único (o mesmo `default_token_generator` da
   recuperação de senha). O token deixa de valer quando a senha é criada.
3. **Senha inutilizável.** A conta é criada como no cadastro pelo Google
   (Sprint 27): `set_unusable_password()` e `full_clean()`. O gerenciador de
   usuários exige uma senha e não serve para esse caso; os testes mostraram
   isso.
4. **Órgão e setor.** O nome digitado é normalizado (espaços) e comparado
   sem diferenciar maiúsculas. Se já existir, a conta é ligada ao existente;
   se estiver inativo, o cadastro é recusado. A unicidade continua garantida
   pelo banco (restrições já existentes).
5. **Consulta aos contratos fictícios.** O acesso usa o `ContractAccess` de
   somente leitura, o mesmo do "Vincular Gestor". Ele vale para os contratos
   com as marcas `[DEMO-APRESENTACAO]` ou `[DEMO-CARTEIRA]` e é concedido
   pelo fiscal responsável de cada contrato, com `ContractSharingEvent` de
   origem "autocadastro". Contratos sem marca não são compartilhados.
6. **Perfil Fiscal.** Como Fiscal, a pessoa não altera os contratos da
   demonstração (somente leitura), mas pode criar um contrato fictício
   próprio, como qualquer fiscal.
7. **Proteções.** Limite por conexão, contado pelos eventos de auditoria da
   última hora (`SELF_SIGNUP_LIMIT_PER_HOUR`); campo oculto anti-robô; recusa
   de e-mail que já tem senha; reenvio do link enquanto a senha não foi
   criada.
8. **Falha no envio.** A conta fica criada, a tela avisa e a pessoa repete o
   cadastro com o mesmo e-mail para receber o link.
9. **Configuração.** `SELF_SIGNUP_ENABLED` vem desligado por padrão e é
   ligado em `settings_demo`, podendo ser desligado pela variável de
   ambiente. As rotas sempre existem e respondem 404 quando desligado.
10. **Depois de criar a senha,** a pessoa volta ao login com a mensagem
    "Senha criada", em vez de entrar direto, para passar pelos mesmos
    controles de sessão e auditoria do login normal.
