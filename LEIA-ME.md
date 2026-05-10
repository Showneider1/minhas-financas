# 🎯 Metas Financeiras — Instalação

## Arquivos gerados

| Arquivo no ZIP           | Cole em...                          |
|--------------------------|-------------------------------------|
| goals_page.py            | pages/goals_page.py                 |
| goal_callbacks.py        | callbacks/goal_callbacks.py         |
| myindex.py               | myindex.py  (substitui o atual)     |
| sidebar.py               | components/sidebar.py (substitui)   |
| callbacks_init.py        | callbacks/__init__.py (substitui)   |
| user.py                  | database/models/user.py (substitui) |

## Como instalar

1. Extraia o ZIP
2. Copie cada arquivo para o destino indicado na tabela
3. Rode a aplicação normalmente:
   python myindex.py
4. Acesse /metas no browser

A tabela `goals` é criada automaticamente pelo create_all() já existente.

## Funcionalidades
- KPIs: Metas Ativas, Total Acumulado, Meta Total, Progresso Geral
- Filtros por Status e Categoria
- Cards com barra de progresso colorida
- Aporte sugerido/mês calculado pelo prazo
- Modal Criar/Editar meta completo
- Modal Registrar Aporte (depósito ou retirada)
- Conclusão automática ao atingir 100%
- Exclusão com soft-delete
- Empty state amigável
