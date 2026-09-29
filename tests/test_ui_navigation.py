"""Testes de roteamento para as novas páginas P1."""

import pages.login_page as login_page
from config.security import create_access_token
from myindex import display_page


def _auth_data():
    return {"token": create_access_token({"sub": "1"})}


def test_investimentos_route_renders_page_when_authenticated():
    content, sidebar_style = display_page("/investimentos", _auth_data())

    assert content is not login_page.layout
    assert content.children is not None
    assert sidebar_style == {"display": "block"}


def test_recorrencia_route_renders_page_when_authenticated():
    content, sidebar_style = display_page("/recorrencia", _auth_data())

    assert content is not login_page.layout
    assert content.children is not None
    assert sidebar_style == {"display": "block"}


def test_importacao_route_renders_page_when_authenticated():
    content, sidebar_style = display_page("/importacao", _auth_data())

    assert content is not login_page.layout
    assert content.children is not None
    assert sidebar_style == {"display": "block"}


def test_analytics_route_renders_page_when_authenticated():
    content, sidebar_style = display_page("/analytics", _auth_data())

    assert content is not login_page.layout
    assert content.children is not None
    assert sidebar_style == {"display": "block"}


def test_new_routes_are_protected_without_token():
    for pathname in ("/investimentos", "/recorrencia", "/importacao", "/analytics"):
        content, sidebar_style = display_page(pathname, None)
        assert content is login_page.layout
        assert sidebar_style == {"display": "none"}
