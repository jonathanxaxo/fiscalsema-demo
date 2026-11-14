# Decisões da Sprint 21

1. **Lógica de IA reaproveitada, não copiada a interface.** Do projeto de
   referência vieram: escolha de modelos (lista configurada ou descoberta dos
   "flash", *lite* primeiro), recuo do `reasoning_effort`
   (minimal → low → none → sem parâmetro em HTTP 400, lembrando o nível por
   modelo), troca de modelo em 403/404/429/5xx/tempo esgotado, parada em 401,
   tempo-limite só até o início da resposta, streaming e formatação segura.
   Reescrito em Python com `http.client` (biblioteca padrão) — sem dependência.
2. **Identidade**: o usuário só vê "Assistente IA" do FiscalSema.
3. **Provedor configurável**: API compatível com OpenAI; trocar de provedor é
   mudar `ASSISTANT_BASE_URL`, `ASSISTANT_MODELS` e `ASSISTANT_API_KEY`.
4. **Somente ajuda na 1ª versão**: `ferramentas.py` define o contrato das
   consultas futuras (serviços internos, permissões, somente leitura) e fica
   desligado.
5. **Conversas no servidor por usuário** (decisão do responsável): tabela
   própria com migração; ninguém vê conversa de outra pessoa, nem o
   Administrador; retenção de 30 dias (limpeza ao abrir o chat).
6. **Auditoria imutável**: o banco proíbe alterar eventos de auditoria; por
   isso o evento é gravado **uma vez, ao final**, com modelo, tempos e se a
   resposta foi concluída — nunca o texto.
7. **Limites**: por minuto (`ASSISTANT_PER_MINUTE`, padrão 6) e por dia
   (`ASSISTANT_DAILY_LIMIT`, padrão 60), contando os eventos da auditoria.
8. **Prompt**: montado no servidor; blocos `<ajuda>` (6.000 caracteres),
   `<perfil>` (300), `<dados>` (5.000, reservado); histórico das últimas 6
   mensagens (4.000 caracteres); pergunta até 2.000. Blocos declarados como
   dados, não instruções.
9. **Velocidade**: só as seções relevantes da ajuda vão ao modelo; modelos
   *lite* e raciocínio mínimo. A meta (1ª palavra ≤ 2 s) e o streaming na
   função Python da Vercel só podem ser medidos no Preview com a chave real.

10. **Região `gru1`** (São Paulo) no `vercel.json`, a mesma do projeto de
    referência, para reduzir a distância até o provedor de IA e os usuários.

## Riscos residuais

- Conteúdo digitado vai ao Google; no nível gratuito pode ser usado para
  melhorar os produtos do provedor (conferir os termos). Mitigação: só dados
  fictícios e aviso permanente.
- Partida a frio da função na Vercel pode somar 1–2 s ao primeiro pedido.
- Se a Vercel acumular a resposta antes de enviar, o texto aparece de uma vez
  (o chat continua funcionando, com o indicador "digitando").
- Se o banco da demo estiver em outra região, cada consulta ao banco fica mais
  lenta com a função em `gru1`: conferir a região do banco após publicar.
