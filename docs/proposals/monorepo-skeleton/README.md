# Esqueletos da proposta monorepo (arquivo morto)

Conteúdo congelado em 27/09/2026 e arquivado em 22/11/2026 por decisão de
arquitetura. **Não é executável e não faz parte do produto.**

O Finance OS em produção é um monólito Python/Dash + SQLAlchemy (ver
`../architecture/CURRENT_ARCHITECTURE.md`). A fonte da verdade do domínio
financeiro é `services/` + `utils/money.py` com `Decimal`, e o contrato canônico
está nos ADRs `docs/decisions/ADR-001` e `ADR-002`.

## O que está aqui

| Caminho original | Conteúdo |
|---|---|
| `apps/web/` | placeholder vazio (Next.js) |
| `packages/ui/`, `packages/financial-core/`, `packages/shared-types/` | esqueletos TS; `financial-core` usa `number` + epsilon, **semântica monetária divergente** do `Decimal` do Python |
| `services/api/` | controllers NestJS + `schema.prisma` com double-entry ledger |
| `infrastructure/` | placeholder vazio |
| `tests/financial-core.test.ts` | teste TS órfão (importava pacote inexistente) |

## Por que foi arquivado

- Nunca houve `tsconfig.json`, `turbo.json`, `package-lock.json` nem build.
- Nenhum código Python ou teste depende desses arquivos.
- A semântica monetária conflitante (`number`/float) era um risco de implementação
  paralela incorreta.

Se a migração para TypeScript for retomada, crie um novo ADR com dono, roadmap e
regra explícita de fonte da verdade antes de trazer qualquer arquivo de volta.
