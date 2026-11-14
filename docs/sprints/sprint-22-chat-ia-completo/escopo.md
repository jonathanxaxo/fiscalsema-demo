# Sprint 22 — Assistente IA como chat completo (correção)

## Problemas relatados no site publicado

1. A caixa de pergunta aceitava só **duas letras**.
2. O responsável pediu que o assistente funcione **como um chat de IA**
   completo, e não apenas como ajuda do sistema.

## Causa e correção

1. O limite `maxlength` (2000) era formatado no padrão brasileiro como
   "2.000", que o navegador lê como **2**. Agora o número sai sem formatação.
2. As regras do prompt passam a permitir conversa geral (explicações,
   redação, resumos, contas, fiscalização de contratos), mantendo a ajuda
   do sistema pela base de conhecimento e todas as proteções: não executa
   ações, não inventa leis/números/fatos, blocos tratados como dados, sem
   acesso a dados cadastrados nesta versão.

## Fora do escopo

Consultar dados cadastrados (continua preparado e desligado).
