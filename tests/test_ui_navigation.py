"""Testes de roteamento para as novas páginas P1."""

import pages.login_page as login_page
from config.security import create_access_token
from myindex import display_page


def _auth_data():
    return {"token": create_access_token({"sub": "1"})}


def test_investimentos_route_renders_page_when_authenticated():
    rendered = display_page("/investimentos", _auth_data())

    assert rendered is not login_page.layout
    assert rendered.children[1].children is not None


def test_recorrencia_route_renders_page_when_authenticated():
    rendered = display_page("/recorrencia", _auth_data())

    assert rendered is not login_page.layout
    assert rendered.children[1].children is not None


def test_new_routes_are_protected_without_token():
    assert display_page("/investimentos", None) is login_page.layout
    assert display_page("/recorrencia", None) is login_page.layout
