"""Contrato de renderer do Dash: todo id referenciado por um callback precisa
existir em algum componente da app — renderizado nos layouts (raiz, páginas e
layouts alternativos) ou declarado como id="..." em código de construção de UI
(inclusive componentes gerados dinamicamente por callbacks).

O app usa suppress_callback_exceptions=True (app.py), o que desliga a validação
de IDs no startup. Sem este contrato, um Input/State/Output apontando para um id
inexistente no DOM faz o renderer abortar o callback no navegador — falha
silenciosa, sem log no servidor. Foi exatamente o bug P0 do State
'data-pagamento' em callbacks/transactions_callbacks.py: o DatePicker foi
removido do modal no commit 488d2d3, mas o callback continuou referenciando-o.
"""

import re
from pathlib import Path

import myindex  # noqa: F401  (define app.layout e importa todos os callbacks)
from app import app
from pages import (
    analytics_page,
    budgets_page,
    cartoes_page,
    configuracoes_page,
    dashboard_page,
    extrato_page,
    goals_page,
    importacao_page,
    investimentos_page,
    login_page,
    recorrencia_page,
    relatorios_page,
    vaults_page,
)

PROJECT_ROOT = Path(myindex.__file__).resolve().parent
ID_LITERAL = re.compile(r"""id=["']([A-Za-z0-9_-]+)["']""")

PAGE_MODULES = (
    analytics_page,
    budgets_page,
    cartoes_page,
    configuracoes_page,
    dashboard_page,
    extrato_page,
    goals_page,
    importacao_page,
    investimentos_page,
    login_page,
    recorrencia_page,
    relatorios_page,
    vaults_page,
)

# Fluxo fantasma de exclusão do dashboard: botões/modal/toast/store removidos
# pela blindagem P0 do "disparo fantasma de exclusão" (DR), mas 4 callbacks em
# callbacks/dashboard_callbacks.py ainda os referenciam. Código morto — nunca
# dispara porque nenhum botão os aciona. Limpar em missão dedicada e, ao fazê-lo,
# esvaziar esta lista.
KNOWN_ORPHANS = {
    "store-acao-pendente",
    "modal-confirmar-exclusao",
    "toast-dashboard",
    "modal-excluir-btn-ok",
    "modal-excluir-btn-cancel",
}


def _walk_ids(component, found):
    if isinstance(component, (list, tuple)):
        for child in component:
            _walk_ids(child, found)
        return
    if isinstance(component, str) or component is None:
        return
    comp_id = getattr(component, "id", None)
    if isinstance(comp_id, str):
        found.add(comp_id)
    _walk_ids(getattr(component, "children", None), found)


def _rendered_ids():
    """Ids presentes nos layouts efetivamente renderizados (raiz + páginas)."""
    found = set()
    _walk_ids(app.layout, found)
    for module in PAGE_MODULES:
        for name in dir(module):
            if name != "layout" and not name.endswith("_layout"):
                continue
            value = getattr(module, name)
            if callable(value):
                value = value()
            if hasattr(value, "children") or hasattr(value, "id"):
                _walk_ids(value, found)
    return found


def _literal_ids():
    """Ids declarados como id="..." em páginas, componentes e callbacks."""
    declared = set()
    for directory in ("pages", "components", "callbacks"):
        for path in sorted((PROJECT_ROOT / directory).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            declared.update(
                ID_LITERAL.findall(path.read_text(encoding="utf-8", errors="ignore"))
            )
    return declared


def _parse_output_ids(key):
    """Extrai ids simples da chave do callback_map (outputs e inputs embutidos)."""
    if key.startswith("..") and key.endswith(".."):
        tokens = key[2:-2].split("...")
    else:
        tokens = [key]
    ids = []
    for token in tokens:
        if token and "." in token:
            dep_id = token.rsplit(".", 1)[0]
            if dep_id and not dep_id.startswith("{"):
                ids.append(dep_id)
    return ids


def _collect_referenced_ids():
    referenced = {}
    for key, spec in app.callback_map.items():
        for dep in spec.get("inputs", []) + spec.get("state", []):
            dep_id = dep["id"]
            if isinstance(dep_id, str) and not dep_id.startswith("{"):
                referenced.setdefault(dep_id, key)
        for dep_id in _parse_output_ids(key):
            referenced.setdefault(dep_id, key)
    return referenced


def _declared_ids():
    return _rendered_ids() | _literal_ids()


def test_todos_os_ids_referenciados_por_callbacks_existem_no_layout():
    declared = _declared_ids()
    referenced = _collect_referenced_ids()

    missing = {
        dep_id: key
        for dep_id, key in sorted(referenced.items())
        if dep_id not in declared and dep_id not in KNOWN_ORPHANS
    }

    assert not missing, (
        "Callbacks referenciam ids que não existem em nenhum layout — "
        f"falha silenciosa do renderer Dash: {missing}"
    )


def test_known_orphans_continua_congelado():
    declared = _declared_ids()

    resolved = KNOWN_ORPHANS & declared

    assert not resolved, (
        "Ids antes órfãos foram materializados no layout — remova-os de "
        f"KNOWN_ORPHANS para voltar a vigiá-los: {sorted(resolved)}"
    )
