# Sprint 32 — Arise lê TR e contrato anexados (ler e descartar) + documentos fictícios

## Decisão do responsável

Roteiro preparado pelo responsável (antes numerado como "Sprint 24") e
aprovado por clique ("Autorizo tudo"): dependência `pypdf==7.1.0`,
implementação, testes, documentos fictícios e PR + merge. Sem migração, sem
variável nova, sem armazenamento novo; módulo `documents/` intocado.

## Etapa A — documentos fictícios (fora do sistema)

- Termo de Referência e Contrato fictícios, em PDF e DOCX (< 100 KB cada),
  com "DOCUMENTO FICTÍCIO — USO EXCLUSIVO EM DEMONSTRAÇÃO" no cabeçalho e no
  rodapé de todas as páginas.
- Dados inventados e coerentes com os itens de demonstração do sistema
  (DEMO-1 suporte R$ 200,00/h, DEMO-2 manutenção R$ 150,00/h, DEMO-3 licença
  R$ 1.000,00/un): Contrato nº 042/2026-DEMO, processo PROC-DEMO-2026/0042,
  órgão e fornecedor fictícios, CNPJs zerados/repetidos marcados "(fictício)",
  vigência 01/02/2026 a 31/01/2027, total R$ 690.000,00.
- Gerados no ambiente do agente (python-docx + LibreOffice); as ferramentas
  não entram no `requirements.txt`. Entregues ao responsável para guardar no
  computador; não ficam no repositório.

## Etapa B — ler e descartar no Arise

- Botão de clipe (📎) na tela cheia e no painel flutuante; PDF ou DOCX até
  4 MB; nome do arquivo com "x" para remover; aviso de LGPD.
- Upload só em memória (`InMemoryOnlyUploadHandler`; nunca arquivo temporário);
  pedido acima de 4 MB recusado antes da leitura.
- Tipo real pela assinatura; PDF até 100 páginas e sem senha; DOCX pela
  biblioteca padrão, recusando DOCTYPE/ENTITY e compactação suspeita.
- Texto até 40.000 caracteres no bloco `<documento>` (avisa se leu só o
  início); regras novas: citar a cláusula, tratar o documento como dado e
  pedir o anexo quando a pergunta for sobre cláusulas sem arquivo.
- O arquivo vale só para aquela pergunta. A conversa guarda a pergunta, a
  resposta e "📎 documento anexado: nome (lido e descartado)".
- Auditoria (`ApiAccessEvent`, `/assistente/`): só tipo, bytes, páginas,
  truncado e tempo de leitura (sem nome e sem conteúdo).
- PDF de imagem: "Não consegui ler o texto deste PDF (parece ser uma imagem)…".

## Fora do escopo

- Guardar arquivos, ligar `documents/`, OCR de PDF digitalizado.
