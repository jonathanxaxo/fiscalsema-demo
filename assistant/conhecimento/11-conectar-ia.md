---
titulo: Conectar uma IA externa ao FiscalSema
rotas: assistant:chat accounts:my_account assistant_drafts:list assistant_drafts:detail
perfis: todos
palavras: conectar configurar ia externa chatgpt codex claude claude code claude desktop mcp oauth url endereco link conector integracao autorizacao seguranca revogar permissao como usar exemplo prompt
---

## Como conectar uma IA externa ao FiscalSema

Explique ao fiscal em linguagem simples, sem detalhes internos de segurança. Para usar uma IA pessoal com o FiscalSema, **não basta colar o link em uma conversa**: é necessário cadastrar o conector nas configurações do aplicativo da IA, entrar na própria conta FiscalSema e autorizar o acesso. A IA só poderá acessar o que a pessoa já tem permissão de visualizar.

**Nome do conector:** FiscalSema.
**Endereço público do conector neste ambiente:** `https://fiscalsema-demo.vercel.app/mcp`.
Esse endereço é a URL pública que o fiscal precisa copiar, não um segredo. Não troque pelo endereço da página inicial. Em outras instalações, consulte **Minha conta → Conexões externas** para obter o endereço correspondente.

### Claude.ai e Claude Desktop

1. No Claude, abra **Configurações/Personalizar → Conectores → Adicionar conector personalizado** (o nome exato do menu pode mudar).
2. Informe o nome **FiscalSema** e cole o endereço acima.
3. Clique em **Conectar**. Entre no FiscalSema pela página de login aberta pelo navegador e leia as permissões solicitadas.
4. Autorize apenas as permissões necessárias. Volte ao Claude e experimente: **"Liste meus contratos autorizados no FiscalSema."**
5. No Claude Desktop, os conectores da conta Claude podem aparecer automaticamente; confira as configurações.

### ChatGPT

1. Se a sua conta permitir adicionar um conector MCP personalizado, procure essa opção em **Configurações → Plugins/Aplicativos**.
2. Informe **FiscalSema**, cole o endereço do conector e siga as etapas de conexão e autorização pelo login do FiscalSema.
3. Faça uma primeira pergunta simples: **"Quais contratos posso consultar pelo FiscalSema?"**

**Atenção:** a disponibilidade de conectores personalizados depende dos recursos da conta ChatGPT. A conexão do ChatGPT com este FiscalSema ainda não foi homologada; não prometa que funcionará em todas as contas.

### Codex no Windows (PowerShell)

Com o Codex instalado, execute no terminal:
```powershell
codex mcp add fiscalsema --url https://fiscalsema-demo.vercel.app/mcp
codex mcp login fiscalsema
codex mcp list
```
Siga a autenticação no navegador quando aparecer. Se ocorrer erro, informe que essa integração ainda requer verificação de compatibilidade; não oriente a desativar proteções.

### Claude Code no Windows (PowerShell)

Com o Claude Code instalado, execute:
```powershell
claude mcp add --transport http fiscalsema https://fiscalsema-demo.vercel.app/mcp
```
Dentro do Claude Code, use `/mcp` para conferir a conexão. **Importante:** atualmente o login remoto do FiscalSema pode não concluir com Claude Code local devido ao redirecionamento de autenticação; cadastrar o link não garante que funcione. Oriente a solicitar suporte para homologar a compatibilidade, sem enfraquecer a segurança.

### Exemplo de pedido para copiar e usar na IA externa

> Utilize o conector MCP FiscalSema para consultar exclusivamente os contratos permitidos para minha conta. Liste os contratos, ordens de serviço, empenhos, notas fiscais e prazos. Se encontrar divergências, apresente o dado atual, a correção sugerida e a justificativa. Não faça nenhuma alteração sem minha autorização pelo processo de confirmação do FiscalSema.

### Cuidados de segurança que o fiscal precisa saber

- Comece permitindo **somente leitura**; outras permissões só quando necessárias.
- A IA pode consultar e analisar somente os registros autorizados para o usuário conectado.
- Propostas de correção ficam em **Rascunhos da IA** para revisão. Uma mensagem como "sim" no chat **não modifica os dados**.
- Para determinadas alterações permitidas é necessária confirmação formal, com código de uso único gerado no FiscalSema. Confira a proposta antes de confirmar.
- A IA **não pode executar pagamentos, atestos, liquidações ou homologações**.
- Nunca forneça sua senha, chave ou token em mensagens do chat.
- Para cancelar uma conexão: **Minha conta → Conexões externas → Revogar**.
- Neste ambiente de demonstração, trabalhe exclusivamente com dados fictícios.

Se a conexão falhar, confirme que o conector foi realmente adicionado, que o login foi concluído e que sua conta tem permissão. Não invente botões, não afirme que clientes não homologados já funcionam e não explique mecanismos internos de autenticação, proteção ou auditoria.
