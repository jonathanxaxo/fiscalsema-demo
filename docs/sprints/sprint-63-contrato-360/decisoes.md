# Decisões — Sprint 63

1. A linha do tempo é uma projeção somente leitura dos registros existentes;
   ela não duplica nem modifica fatos financeiros.
2. Detalhes internos em formato estruturado dos eventos não são enviados ao
   template; a interface recebe apenas rótulos e referências seguras.
3. O acesso reaproveita `contracts_visible_to`; abrir a URL não amplia o
   escopo do perfil.
4. Valor e vigência atuais são apresentados ao lado dos dados originais para
   preservar contexto e rastreabilidade.
