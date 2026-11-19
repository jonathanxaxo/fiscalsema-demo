# Testes — Sprint 55

## Evidência local

- classificador por unidade estruturada: aprovado;
- unidade personalizada sem regra: permanece não classificada;
- modalidades estruturadas mensal, hora, unidade, serviço, licença, usuário,
  turma, lote, UST, HST e USN: mapeadas sem inferência pelo nome;
- calculadora decimal com regra confirmada: aprovada;
- regra não confirmada: cálculo recusado;
- confirmação individual da modalidade do item: coberta na suíte integrada;
- abertura da inteligência por Gestor do Contrato: não altera o achado;
- checagem de modelos e migrações: aprovada;
- compilação Python e `git diff --check`: aprovados.

Os casos integrados de persistência, leitura de PDF, autorização por perfil,
resolução e reabertura estão em
`contracts/test_profiles_intelligence.py` e aguardam execução na CI com
PostgreSQL.
