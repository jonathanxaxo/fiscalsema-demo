# Sprint 43 — Cadastrar NF em OS com serviços do catálogo

## Solicitação

"Não tem como incluir notas fiscais da OS" — o botão não aparecia para quem
usava OS com serviços do catálogo (resposta do usuário).

## Diagnóstico

- A regra de permissão não mudou: o link "Cadastrar Nota Fiscal" já existia,
  mas só como link pequeno no rodapé da OS. Na OS com catálogo a página fica
  longa e o link não era encontrado.
- O serviço homologado mostrava "Pronto para faturar" sem nenhuma ação.
- No formulário da NF, sem serviço homologado, a lista "Serviços cobrados"
  aparecia vazia e sem explicação.

## Correção (somente tela; nenhuma regra muda)

- Botão **Cadastrar Nota Fiscal** no título da seção "Notas fiscais" da OS.
- Aviso na seção: serviços do catálogo só são marcados na NF depois de
  homologados; a NF pode ser cadastrada sem marcar serviços.
- Serviço homologado ainda não cobrado: link **"Pronto para faturar ·
  cadastrar NF"**, que abre a NF com o serviço já marcado.
- Formulário: quando não há serviço disponível, explica o motivo.

As validações das Sprints 38–39 continuam iguais (só serviço homologado,
sem repetir em NF ativa, total da NF limitado ao valor da OS).
