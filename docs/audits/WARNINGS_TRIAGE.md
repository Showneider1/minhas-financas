# WARNINGS TRIAGE - Finance OS
**Data:** 2026-09-27
**Executor:** QA Engineer
**Comando executado:** `pytest -W default -q`
**Repositório:** `/mnt/c/Users/rapha/Documents/Scripts Python/Minhas_Financas`

## Resumo Executivo
Execução do suite de testes com `-W default` retornou **81 warnings distintos** reportados pelo pytest, com repetição por teste chegando a ~222 emissões observadas no log bruto. Quatro categorias principais foram mapeadas:

1. `PydanticDeprecatedSince20` - class config / @validator / .dict()
2. `SQLAlchemy MovedIn20Warning` - `declarative_base`
3. `DeprecationWarning datetime.datetime.utcnow()` - origem SQLAlchemy
4. `ResourceWarning unclosed database` - SQLite

## 1. PydanticDeprecatedSince20

### Causa
Pydantic v2 depreca `class Config` em favor de `ConfigDict`, `@validator` V1 em favor de `@field_validator` e `BaseModel.dict()` em favor de `model_dump()`.

### Origem e Frequência
| Arquivo | Linha | Tipo |
|---------|-------|------|
| schemas/account_schema.py | 47 | class Config |
| schemas/budget_schema.py | 23 | class Config |
| schemas/category_schema.py | 21 | @validator |
| schemas/category_schema.py | 55 | class Config |
| schemas/transaction_schema.py | 83 | @validator |
| schemas/transaction_schema.py | 135 | @validator |
| schemas/transaction_schema.py | 155 | class Config |
| schemas/user_schema.py | 36 | @validator |
| schemas/user_schema.py | 85 | class Config |
| services/finance_service.py | 94 | .dict() |

Frequência observada: 9 mensagens distintas no summary, replicadas em múltiplos testes. Estimativa de emissões totais: ~70.

### Impacto
- Falha futura em Pydantic v3.
- Ruído no CI, dificulta identificação de warnings reais.
- Não quebra funcionalidade hoje.

### Tratativa adotada
**Corrigível rapidamente parcial.**
- `class Config -> ConfigDict`: mudança mecânica, baixo risco, 5 arquivos.
- `@validator -> @field_validator`: requer revisão de lógica, médio risco.
- `.dict() -> model_dump()`: mudança pontual já identificada.

**Decisão QA:** Não bloquear release. Criar ticket técnico para migração Pydantic v2 completa no próximo sprint. Enquanto isso, **não ignorar** para manter visibilidade.

## 2. SQLAlchemy MovedIn20Warning

### Causa
`declarative_base()` movido de `sqlalchemy.ext.declarative` para `sqlalchemy.orm.declarative_base()` desde SQLAlchemy 2.0.

### Origem e Frequência
- `database/base.py:8` `Base = declarative_base()`
- `database/base.py:5` `from sqlalchemy.ext.declarative import declarative_base`

Frequência: 1 warning por sessão, reportado no summary.

### Impacto
Baixo. Apenas aviso de deprecação, funcionalidade mantida por compatibilidade.

### Tratativa adotada
**Corrigível rapidamente.**
Mudar import para:
```python
from sqlalchemy.orm import declarative_base

Base = declarative_base()
```
**Decisão QA:** Corrigir em hotfix técnico. Não sistêmico.

## 3. DeprecationWarning datetime.datetime.utcnow()

### Causa
`datetime.datetime.utcnow()` está depreciado no Python 3.12+ e será removido. Aviso emitido **dentro da biblioteca SQLAlchemy 2.0.36** em `sqlalchemy/sql/schema.py:3596` ao envolver callables.

### Origem e Frequência
- Origem externa: `venv/Lib/site-packages/sqlalchemy/sql/schema.py:3596`
- Testes afetados: test_investment_math.py:12, test_user_isolation.py:3, test_transaction_contract.py, etc.
Frequência total estimada: ~71 emissões.

### Impacto
Nenhum impacto funcional no código da aplicação. Ruído alto no CI.

### Tratativa adotada
**Sistêmico — não corrigível no código próprio.**
A origem é interna ao SQLAlchemy. Possível mitigação:
- Atualizar SQLAlchemy para versão que corrige uso interno de `utcnow`.
- Ignorar temporariamente via filterwarnings.

**Decisão QA:** Ignorar temporariamente no pytest para evitar poluir CI. Não suprimir em desenvolvimento local com `-W default`.

Config sugerida em `pyproject.toml`:
```toml
[tool.pytest.ini_options]
filterwarnings = [
    "ignore:datetime.datetime.utcnow\\(\\) is deprecated:DeprecationWarning:sqlalchemy.sql.schema",
]
```

## 4. ResourceWarning unclosed database

### Causa
`ResourceWarning: unclosed database in <sqlite3.Connection object ...>` emitido ao final da sessão pytest.

### Origem e Frequência
- `<sys>:0` ao final do run.
- Provável origem em fixtures de teste que criam conexão SQLite em memória sem fechar explicitamente ou dependem de GC.

### Impacto
Leak de recurso em testes, pode gerar flakiness em pipelines com restrição de FD.

### Tratativa adotada
**Potencialmente sistêmico.**
Revisar `tests/conftest.py` e fixtures de banco para garantir `close()` / `engine.dispose()` no teardown.

**Decisão QA:** Não ignorar de forma cega. Primeiro investigar conftest. Caso seja limitação do pytest-sqlalchemy com SQLite em memória, pode-se adicionar `PYTHONWARNINGS="ignore::ResourceWarning"` apenas no CI enquanto a fixture é refatorada.

Config temporária sugerida:
```toml
filterwarnings = [
    "ignore::ResourceWarning",
]
```

## Proposta de Configuração Temporária

Para evitar poluição do CI sem perder visibilidade local, adicionar em `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Warnings sistêmicos de bibliotecas externas e recursos de teste
filterwarnings = [
    "ignore:datetime.datetime.utcnow\\(\\) is deprecated:DeprecationWarning:sqlalchemy.sql.schema",
    # "ignore::ResourceWarning", # liberar após revisão de fixtures
    # "ignore::sqlalchemy.exc.MovedIn20Warning", # remover após correção do import
    # "ignore::pydantic.warnings.PydanticDeprecatedSince20", # manter visível para migração
]
```

**Princípio:** Ignorar apenas warnings sistêmicos fora do controle do código. Manter warnings de Pydantic visíveis para forçar migração.

## Ações Recomendadas

1. **P0 - Hotfix:** Corrigir import `declarative_base` em `database/base.py`.
2. **P1 - Técnico:** Planejar migração Pydantic v2: `ConfigDict`, `field_validator`, `model_dump`.
3. **P1 - DevOps:** Aplicar `filterwarnings` acima no `pyproject.toml` para DeprecationWarning do SQLAlchemy.
4. **P2 - QA:** Auditar `tests/conftest.py` para garantir fechamento de conexões SQLite e eliminar `ResourceWarning`.

## Conclusão QA
Nenhum warning representa risco imediato para cálculos financeiros. Os warnings de Pydantic e SQLAlchemy import são corrigíveis rapidamente. O `DeprecationWarning` de `utcnow` e `ResourceWarning` são sistêmicos e podem ser ignorados temporariamente no CI após aprovação do Arquiteto.

**Assinatura:** QA Engineer - Finance OS
