# Sprint 57 — Login demonstrativo multiperfil e carteira fictícia

## História de usuário

- **COMO:** responsável pela demonstração do FiscalSema;
- **QUERO:** entrar somente com `admin@exemplo.com.br` e alternar entre os cinco
  perfis funcionais, mantendo a mesma senha;
- **PARA:** testar e apresentar todas as visões sem compartilhar vários logins.

Como complemento, todas as contas ativas e regulares dos cinco perfis devem
encontrar dados exclusivamente fictícios adequados ao próprio escopo.

## Entregas

- uma única conta controladora autorizada a selecionar os cinco perfis;
- contas internas de perfil com senha inutilizável e ocultas da gestão comum;
- permissões reais do backend preservadas durante cada troca;
- troca direta entre perfis, retorno ao perfil original e auditoria;
- carga idempotente de contratos classificados, itens, empenhos, OS,
  execuções, notas fiscais e pagamentos fictícios;
- vínculo individual `READ_ONLY` para cada Gestor do Contrato ativo;
- carteira integral para Auxiliar Administrativa e Gestor Administrativo,
  conforme as regras já aprovadas;
- fluxo manual único, confirmado no GitHub Actions, para preparar perfis e
  carteira depois das migrations.

## Fora do escopo

- alterar a senha ou o perfil persistido da conta controladora;
- conceder troca de perfil a outra conta;
- copiar dados, documentos, usuários ou credenciais de ambiente real;
- incluir contas inativas, bloqueadas, arquivadas ou legadas na carga;
- remover fisicamente os dados fictícios depois de criados;
- modificar logotipo, lupa, favicon ou animações;
- deploy ou execução do fluxo no banco da demo sem nova autorização.
