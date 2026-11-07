# Decisões da Sprint 14

1. Código trazido do sistema principal por leitura do repositório (sem acesso
   a banco, VM ou dados reais) e adaptado; referências ao repositório real não
   são versionadas, conforme a política da demo.
2. O sino complementa a "Central de trabalho" do painel (mantida), em vez de
   substituí-la, porque o painel foi aprovado na Sprint 13.
3. O cálculo é preguiçoso (`SimpleLazyObject`): só roda quando a página
   exibe o sino.
4. Defeito encontrado nas capturas: títulos longos cortados. Causa: regra
   antiga `.user-menu a { white-space: nowrap }`, mais específica que a regra
   do sino. Correção: restringir a regra antiga aos links diretos
   (`.user-menu > a`), com teste de regressão.
