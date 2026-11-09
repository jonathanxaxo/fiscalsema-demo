# Decisões da Sprint 18

1. **Espaço que não quebra em vez de novo filtro de moeda.** Mantém exatamente
   a formatação atual dos números (sem risco de mudar casas decimais) e resolve
   a quebra em todas as telas, inclusive tabelas e celular.
2. **Letra ajustada à largura do quadro (`container-type` + `cqi`).** Com
   valores na casa dos bilhões, o número inteiro não cabe no tamanho antigo;
   reduzir a letra só o necessário mantém todos os quadros iguais, em uma
   linha, sem cortar o valor. Teto: o tamanho anterior.
3. **Algarismos de largura fixa** (`tabular-nums`) para os valores alinharem.
4. **Numeração:** a Sprint 17 foi usada pelo workflow com IA e MCP; esta
   correção é a Sprint 18 e o "Acompanhamento mensal de OS" passa a ser a 19.
