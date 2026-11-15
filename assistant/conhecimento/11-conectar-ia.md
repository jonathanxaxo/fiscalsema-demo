---
titulo: Conectar uma IA externa (Claude) ao FiscalSema
rotas: accounts:my_account assistant_drafts:list assistant_drafts:detail
perfis: todos
palavras: conectar conector claude chatgpt mcp oauth autorizar revogar conexão conexões externas código confirmação executar proposta
---
Você pode conectar um cliente de IA (ex.: Claude no claude.ai ou no Claude Desktop) ao FiscalSema com o **seu próprio login**:

1. No Claude: Configurações → Conectores → **Adicionar conector personalizado**. Nome: FiscalSema Demo. URL: `https://fiscalsema-demo.vercel.app/mcp`.
2. Clique em **Conectar**, entre no FiscalSema e, na tela **Autorizar**, escolha as permissões:
   - **consultar** (ler o que você já pode ver);
   - **propor rascunhos** (ficam pendentes da sua confirmação);
   - **executar propostas com código** (só com o código que você gera).
3. Para cortar o acesso: **Minha conta → Conexões externas → Revogar**.

Como a IA altera algo com segurança:
- Ela só **propõe**; a proposta aparece em **Rascunhos da IA** e vale 24 horas.
- Você confere o antes/depois e clica em **Aprovar e executar**, ou em **Gerar código de confirmação** e digita o código (vale 10 minutos, uso único) no chat.
- Um "sim" no chat não executa nada. Nunca passe o código sem conferir a proposta.
- Pagamentos nunca são executados pela IA; homologação, atesto e liquidação também não.

A IA vê só os contratos que você vê. Cada chamada fica registrada na auditoria.
