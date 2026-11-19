# Decisões — Sprint 54

1. O perfil Fiscal Substituto continua sendo uma delegação temporária e
   auditada, não um sexto perfil permanente.
2. O Gestor Administrativo representa Superintendente e Secretário e, por
   decisão do responsável, enxerga todos os contratos ativos da demonstração.
3. A Auxiliar pode solicitar uma conferência automatizada, mas não corrige
   cadastro operacional nem abre o arquivo privado; recebe somente achados e
   metadados administrativos.
4. Contas `USUARIO_CONSULTA` existentes não são convertidas automaticamente.
   Ficam marcadas para reclassificação auditada pelo Administrador Geral.
5. Autorização é aplicada nas consultas e serviços do backend. Ocultar botão
   na tela é apenas uma segunda camada de apresentação.
6. Todo vínculo individual de contrato permanece tecnicamente `READ_ONLY`.
   O Administrador Geral pode auditá-lo e revogar incompatibilidades ao alterar
   um perfil, mas o compartilhamento operacional continua reservado ao Fiscal
   Titular responsável.
7. Abrir uma tela ou consultar a API não altera achados nem registros
   operacionais. Perfis somente leitura também não recebem capacidade de
   rascunho controlado, mesmo que uma credencial técnica esteja mal configurada.

## Riscos controlados

- a migração preserva valores legados para evitar perda de acesso ou
  reclassificação incorreta;
- alterações de perfil encerram sessões e revogam vínculos incompatíveis;
- o último Administrador ativo continua protegido contra rebaixamento.
