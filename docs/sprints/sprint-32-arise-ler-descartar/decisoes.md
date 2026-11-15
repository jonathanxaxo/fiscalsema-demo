# Decisões — Sprint 32

1. **pypdf** (Python puro, BSD-3, sem dependências) para PDF; DOCX com
   `zipfile` + `xml.etree` da biblioteca padrão.
2. **Upload só em memória**: o leitor padrão do Django grava em arquivo
   temporário acima de 2,5 MB; trocamos o leitor só nesta rota (com
   `csrf_exempt` + `csrf_protect`, para manter o CSRF) e recusamos pedidos
   acima de 4 MB antes de ler.
3. **Tipo real pelo conteúdo**, não pela extensão.
4. **Uma pergunta, um documento**: o texto não fica no histórico; perguntas
   seguintes pedem o anexo de novo. Evita guardar conteúdo de documento.
5. **Auditoria sem nome do arquivo**: o nome pode revelar informação; fica só
   na conversa da própria pessoa.
6. **Documentos fictícios fora do repositório**: o roteiro pede que fiquem só
   no computador do responsável.
7. **Correção visual**: valores "R$" com espaço que não quebra nos documentos
   e caixa de texto que não empurra o botão Enviar no celular.
