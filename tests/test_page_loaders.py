"""Reatividade e carregamento de listas no mount.

Bug P0 corrigido: load_credit_cards (e os loaders irmãos de investimentos e
recorrência) tinham prevent_initial_call=True e escutavam apenas stores que não
mudam na entrada da página (auth-store só muda no login; o reload-trigger monta
com seu valor inicial) — a lista nunca carregava no mount, o usuário via
"cadastra, mas não mostra". Os loaders agora seguem o padrão do dashboard:
initial call liberado, disparando quando os componentes da página montam.

Este módulo trava duas propriedades:
1. Os loaders permitem o initial call (grafo servido ao browser).
2. O fluxo completo de cartões funciona em nível de dispatch HTTP real:
   salvar cartão → store notifica → listagem renderiza o novo cartão.
"""

import json

import myindex  # noqa: F401  (monta app.layout e registra todos os callbacks)
from app import app

LOADERS = {
    "cartoes-list-container.children": "Cartões",
    "invest-portfolio-table.children": "Investimentos",
    "recurrence-table.children": "Recorrências",
}


def _patch_dispatch_env(db_engine, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    import database.connection as conn
    import middleware.rate_limiter as rl

    factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(conn, "SessionLocal", factory)
    monkeypatch.setattr(rl, "SessionLocal", factory)


def test_loaders_disparam_no_mount(db_engine, monkeypatch):
    _patch_dispatch_env(db_engine, monkeypatch)

    client = myindex.server.test_client()
    deps = json.loads(client.get("/_dash-dependencies").data)

    by_output = {d["output"]: d for d in deps}
    assert set(LOADERS) <= set(by_output)

    for output, name in LOADERS.items():
        assert by_output[output]["prevent_initial_call"] is False, (
            f"Loader de {name} ({output}) precisa permitir o initial call — "
            "com prevent_initial_call=True a lista nunca carrega na entrada "
            "da página (bug P0 'cadastra, mas não mostra')."
        )


def test_fluxo_cartoes_cadastra_notifica_e_lista(db_engine, monkeypatch):
    _patch_dispatch_env(db_engine, monkeypatch)

    import callbacks.cartoes_callbacks as cc

    monkeypatch.setattr(cc, "resolve_user", lambda *a, **kw: 1)

    client = myindex.server.test_client()

    save_key = next(
        k
        for k in app.callback_map
        if "cartoes-reload-trigger.data@" in k and "cartoes-feedback.children" in k
    )

    save_payload = {
        "output": save_key,
        "outputs": [
            {"id": "credit-card-feedback", "property": "children"},
            {"id": "cartoes-feedback", "property": "children"},
            {"id": "cartoes-feedback", "property": "is_open"},
            {"id": "cartoes-reload-trigger", "property": "data"},
            {"id": "modal-credit-card", "property": "is_open"},
        ],
        "inputs": [
            {"id": "btn-save-credit-card-modal", "property": "n_clicks", "value": 1}
        ],
        "state": [
            {"id": "credit-card-nome", "property": "value", "value": "Nubank"},
            {"id": "credit-card-limite", "property": "value", "value": "5000"},
            {"id": "credit-card-fechamento", "property": "value", "value": 3},
            {"id": "credit-card-vencimento", "property": "value", "value": 10},
            {"id": "auth-store", "property": "data", "value": {"token": "x"}},
            {"id": "cartoes-reload-trigger", "property": "data", "value": 0},
        ],
        "changedPropIds": ["btn-save-credit-card-modal.n_clicks"],
    }

    resp = client.post("/_dash-update-component", json=save_payload)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["response"]["cartoes-reload-trigger"]["data"] == 1
    assert "Nubank" in json.dumps(body)

    def _list_payload(trigger_value, changed):
        return {
            "output": "cartoes-list-container.children",
            "outputs": {"id": "cartoes-list-container", "property": "children"},
            "inputs": [
                {"id": "auth-store", "property": "data", "value": {"token": "x"}},
                {
                    "id": "cartoes-reload-trigger",
                    "property": "data",
                    "value": trigger_value,
                },
            ],
            "state": [],
            "changedPropIds": [changed],
        }

    resp_reactive = client.post(
        "/_dash-update-component", json=_list_payload(1, "cartoes-reload-trigger.data")
    )
    assert resp_reactive.status_code == 200
    assert "Nubank" in json.dumps(resp_reactive.get_json())

    resp_mount = client.post(
        "/_dash-update-component", json=_list_payload(0, "auth-store.data")
    )
    assert resp_mount.status_code == 200
    assert "Nubank" in json.dumps(resp_mount.get_json())
