# Decisões — Sprint 39

1. Regra do Light mantida: a NF deve ter exatamente o valor dimensionado;
   diferente → devolver. O sistema aponta, a pessoa decide.
2. Devolução preserva a NF no histórico (nada é apagado) e a retira dos
   cálculos por um único filtro (`active()`), aplicado em cada soma.
3. OS com NF devolvida continua exigindo tratamento antes de cancelar
   (regra existente mantida, mais conservadora).
4. A IA continua sem confirmar, homologar, devolver ou pagar.
