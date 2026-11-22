# LGPD — plano de conformidade (planejado, não implementado)

Revisado em 22/11/2026. Nenhum dado financeiro foi excluído ou anonimizado
automaticamente. A execução de exclusão de registros financeiros exige
**aprovação humana explícita** e trilha de auditoria.

## Situação atual

- `database/repositories/user_repo.py::soft_delete_user()` existe, mas **não é chamado**
  por nenhum fluxo da aplicação.
- `database/models/user.py::is_deleted` é preenchido, mas os dados financeiros
  relacionados (transações, contas, investimentos) permanecem.
- Exportações atuais (`services/export_service.py`, `callbacks/relatorios_callbacks.py`)
  são relatórios parciais, não portabilidade completa.
- E-mails completos aparecem em logs de autenticação e auditoria — reduzir conforme
  princípio da necessidade (art. 6º).

## Direitos do titular (art. 18) — plano

| Direito | Implementação prevista | Status |
|---|---|---|
| Acesso / portabilidade | Rota "Meus dados" gerando JSON com todas as entidades do `user_id` (usuário, contas, categorias, transações, cartões, metas, orçamentos, investimentos, recorrências, caixinhas) | Planejado |
| Retificação | Já disponível nos CRUDs por `user_id` | Parcial |
| Eliminação | Fluxo em duas etapas: (1) anonimizar PII do usuário; (2) mediante confirmação explícita, remover/anonimizar lançamentos financeiros preservando a trilha de auditoria em formato agregado | Planejado — **requer aprovação** |
| Revogação de consentimento | Revogar refresh tokens + marcar `@revoked` na exclusão | Planejado |
| Informação | Política de privacidade e prazos de retenção a publicar | Planejado |

## Prazos de retenção (proposta — validar com juridídico)

| Categoria | Retenção proposta | Justificativa |
|---|---|---|
| Dados cadastrais | enquanto a conta existir + 30 dias | execução do contrato |
| Transações e comprovantes | 5 anos | obrigação fiscal/contábil (IRPF) |
| Logs de autenticação/auditoria | 180 dias, com rotação | segurança, art. 46 |
| Tokens de reset/refresh | até expiração ou revogação | menor prazo necessário |
| Rate limit / tentativas de login | 24 h (limpeza pendente — ver ADR-005) | prevenção a abuso |

## Próximos passos concretos

1. Implementar "Meus dados" (somente leitura, reversível).
2. Documentar base legal e política de privacidade.
3. Conectar `soft_delete_user()` a um fluxo de anonimização com revogação de sessões.
4. Definir, com aprovação, o destino dos registros financeiros na eliminação.
5. Limpar PII dos logs e implementar rotação do `audit_log`.
