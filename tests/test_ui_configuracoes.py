"""Testes de UI da página de Configurações (Contas, Cartões e Categorias)."""

from contextlib import contextmanager
from types import SimpleNamespace

import dash_bootstrap_components as dbc
from dash import no_update

import callbacks.config_callbacks as config_callbacks
from config.security import create_access_token
from myindex import display_page


def _walk(component, ids=None):
    if ids is None:
        ids = set()
    cid = getattr(component, "id", None)
    if cid:
        ids.add(cid)
    children = getattr(component, "children", None)
    if children is None:
        return ids
    if isinstance(children, (list, tuple)):
        for child in children:
            _walk(child, ids)
    else:
        _walk(children, ids)
    return ids


def test_configuracoes_page_contains_action_buttons_and_modals():
    auth = {"token": create_access_token({"sub": "1"})}
    content, _ = display_page("/configuracoes", auth)
    ids = _walk(content)

    assert "config-action-buttons" in ids
    assert "modal-categoria" in ids
    assert "modal-conta" in ids
    assert "modal-cartao" in ids


def test_render_action_button_returns_correct_button_per_tab():
    result = config_callbacks.render_action_button("tab-categorias", "/configuracoes")
    assert isinstance(result, dbc.Button)
    assert result.id == "btn-open-cat-modal"

    result = config_callbacks.render_action_button("tab-contas", "/configuracoes")
    assert isinstance(result, dbc.Button)
    assert result.id == "btn-open-acc-modal"

    result = config_callbacks.render_action_button("tab-cartoes", "/configuracoes")
    assert isinstance(result, dbc.Button)
    assert result.id == "btn-open-card-modal"

    result = config_callbacks.render_action_button("tab-categorias", "/dashboard")
    assert result == ""


def test_toggle_modal_conta_opens_and_closes(monkeypatch):
    monkeypatch.setattr(
        config_callbacks,
        "ctx",
        SimpleNamespace(triggered_id="btn-open-acc-modal"),
    )
    opened = config_callbacks.toggle_modal_conta(1, 0)
    assert opened == (True, "", 0, "")

    monkeypatch.setattr(
        config_callbacks,
        "ctx",
        SimpleNamespace(triggered_id="btn-cancel-acc"),
    )
    closed = config_callbacks.toggle_modal_conta(1, 1)
    assert closed == (False, no_update, no_update, "")


def test_toggle_modal_cartao_opens_and_closes(monkeypatch):
    monkeypatch.setattr(
        config_callbacks,
        "ctx",
        SimpleNamespace(triggered_id="btn-open-card-modal"),
    )
    opened = config_callbacks.toggle_modal_cartao(1, 0)
    assert opened == (True, "", "")

    monkeypatch.setattr(
        config_callbacks,
        "ctx",
        SimpleNamespace(triggered_id="btn-cancel-card"),
    )
    closed = config_callbacks.toggle_modal_cartao(1, 1)
    assert closed == (False, no_update, "")


def test_toggle_modal_categoria_opens(monkeypatch, db, sample_user):
    monkeypatch.setattr(
        config_callbacks,
        "ctx",
        SimpleNamespace(triggered_id="btn-open-cat-modal"),
    )

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(config_callbacks, "get_db_session", session_ctx)
    monkeypatch.setattr(
        config_callbacks,
        "resolve_user",
        lambda *args, **kwargs: sample_user.id,
    )

    opened = config_callbacks.toggle_modal_categoria(1, 0, {"token": "valid"})
    assert opened[0] is True
    assert opened[2] == ""
    assert opened[3] == "EXPENSE"
    assert opened[4] == "#3498db"
    assert opened[5] == ""
