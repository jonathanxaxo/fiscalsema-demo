# Decisões — Sprint 61

1. **Rótulo do formulário como nome do campo.** O nome mostrado vem do mesmo
   formulário usado na tela de cadastro (`FORM_CLASSES` em `api_v1/drafts.py`),
   para o fiscal ver o mesmo texto que já conhece. Sem rótulo, usa o nome do
   campo no modelo.
2. **Formatação só na exibição.** A conversão para reais, datas e números em
   pt-BR acontece apenas na tela. O rascunho, a comparação e as evidências
   gravados não mudam, e a confirmação continua validando os dados originais.
3. **JSON preservado, mas recolhido.** O código técnico continua disponível em
   "Ver dados técnicos (para auditoria)", para quem precisar conferir o dado
   bruto. O fiscal não precisa abrir essa área para decidir.
4. **Situações em palavras.** As classificações técnicas (`NOVO`,
   `DIVERGENTE`, `NAO_CONFIAVEL`…) viram frases curtas; as que pedem atenção
   dizem "conferir".
5. **Sem mudança de regra.** Permissões, confirmação humana, código de uso
   único, bloqueio de pagamento pela IA e auditoria ficam como estavam.
