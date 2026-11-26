# Sprint 71 — Contexto contratual seguro no Arise

## História de usuário

- **COMO:** pessoa autenticada em um perfil funcional;
- **QUERO:** conversar com o Arise sobre o contrato selecionado no painel;
- **PARA:** receber somente informações daquele contrato, sem mistura com outro
  contrato ou com uma conversa iniciada em contexto diferente.

## Critérios de aceite

- o chat flutuante e a tela cheia mostram o contrato ativo validado;
- o identificador é aceito somente quando pertence ao escopo autorizado do
  perfil atual;
- identificadores inválidos, contratos sem acesso e arquivados falham antes
  de chamar o provedor de IA;
- ao trocar de contrato, uma nova conversa é criada e o histórico anterior é
  preservado no contrato original;
- continuar no mesmo contrato preserva o histórico;
- ausência de seleção mantém o escopo geral já permitido ao perfil;
- nenhuma fórmula financeira, permissão funcional ou ação de escrita é
  ampliada.

## Fora do escopo

- alterar painéis, cálculos ou permissões existentes;
- clonar ou enviar voz para serviço externo;
- produzir vídeo, capa ou aplicar a nova identidade visual;
- realizar commit, push, merge, deploy ou publicação.
