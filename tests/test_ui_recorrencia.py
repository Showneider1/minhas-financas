"""Testes unitários dos callbacks da página de Contas Recorrentes."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import no_update

import callbacks.recorrencia_callbacks as rec_callbacks
from database.enums import AccountType, BillRecurrence, BillType
from database.models.account import Account
from database.models.category import Category, TransactionType
from database.models.scheduled_bill import ScheduledBill
from database.models.user import User
from services.scheduled_bill_service import ScheduledBillService


def _call_save(**overrides):
    defaults = {
        "n_clicks": 1,
        "auth_data": {"token": "teste"},
        "edit_id": None,
        "name": None,
        "bill_type": None,
        "amount": None,
        "due_date": None,
        "recurrence": None,
        "account_id": None,
        "category_id": None,
        "notes": None,
    }
    defaults.update(overrides)
    return rec_callbacks.save_recurrence(**defaults)


def _patch_runtime(monkeypatch, db, user_id=None):
    monkeypatch.setattr(rec_callbacks, "hit", lambda *args, **kwargs: (True, None))
    monkeypatch.setattr(rec_callbacks, "client_ip", lambda: "127.0.0.1")

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(rec_callbacks, "get_db_session", session_ctx)
    if user_id is not None:
        monkeypatch.setattr(rec_callbacks, "resolve_user", lambda *args, **kwargs: user_id)


def test_save_recurrence_without_clicks_returns_no_update(db, monkeypatch):
    _patch_runtime(monkeypatch, db, user_id=1)

    result = _call_save(n_clicks=None)

    assert result == (no_update, no_update, no_update, no_update)


def test_save_recurrence_invalid_auth_returns_warning_alert(db, monkeypatch):
    _patch_runtime(monkeypatch, db)

    result = _call_save(auth_data={})

    modal_alert = result[0]
    assert isinstance(modal_alert, dbc.Alert)
    assert modal_alert.color == "warning"
    assert "Sessão" in modal_alert.children
    assert result[1] is True


def test_save_recurrence_requires_required_fields(db, monkeypatch, sample_user):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)

    result = _call_save(name=None, amount=100, due_date="2027-01-10")

    modal_alert = result[0]
    assert isinstance(modal_alert, dbc.Alert)
    assert modal_alert.color == "warning"
    assert "obrigatórios" in modal_alert.children
    assert result[1] is True


def test_save_recurrence_success_returns_success_alert(
    db, monkeypatch, sample_user, sample_account, sample_category
):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)

    result = _call_save(
        name="Internet",
        bill_type="payable",
        amount=99.90,
        due_date="2027-01-10",
        recurrence="monthly",
        account_id=str(sample_account.id),
        category_id=str(sample_category.id),
        notes="teste",
    )

    assert result[0] == ""
    assert result[1] is False
    success_alert = result[2]
    assert isinstance(success_alert, dbc.Alert)
    assert success_alert.color == "success"
    assert "Recorrência criada com sucesso." in success_alert.children
    assert result[3] is True

    bills = db.query(ScheduledBill).filter(ScheduledBill.user_id == sample_user.id).all()
    assert len(bills) == 1
    assert bills[0].name == "Internet"
    assert bills[0].recurrence.value == "monthly"


def _create_monthly_bill(db, user_id):
    return ScheduledBillService(db).create_bill(
        user_id=user_id,
        name="Assinatura",
        amount="99.90",
        bill_type=BillType.PAYABLE,
        due_date=date(2027, 1, 10),
        recurrence=BillRecurrence.MONTHLY,
    )


def _patch_trigger(monkeypatch, action_type, bill_id):
    monkeypatch.setattr(
        rec_callbacks,
        "_get_triggered_id",
        lambda: {"type": action_type, "index": bill_id},
    )


def test_pause_recurrence_updates_status(db, monkeypatch, sample_user):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)
    bill = _create_monthly_bill(db, sample_user.id)
    _patch_trigger(monkeypatch, "btn-pause-recurrence", bill.id)

    result = rec_callbacks.manage_recurrence_action([1], [], [], {"token": "ok"})

    db.refresh(bill)
    assert bill.is_paused is True
    assert result[0].color == "success"
    assert "pausada" in result[0].children
    assert result[1] is True
    assert result[2] is not None


def test_resume_recurrence_updates_status(db, monkeypatch, sample_user):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)
    bill = _create_monthly_bill(db, sample_user.id)
    rec_callbacks.BillRecurrenceService(db).set_paused(bill.id, sample_user.id, True)
    _patch_trigger(monkeypatch, "btn-resume-recurrence", bill.id)

    result = rec_callbacks.manage_recurrence_action([], [1], [], {"token": "ok"})

    db.refresh(bill)
    assert bill.is_paused is False
    assert result[0].color == "success"
    assert "retomada" in result[0].children


def test_cancel_recurrence_updates_status(db, monkeypatch, sample_user):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)
    bill = _create_monthly_bill(db, sample_user.id)
    _patch_trigger(monkeypatch, "btn-cancel-recurrence", bill.id)

    result = rec_callbacks.manage_recurrence_action([], [], [1], {"token": "ok"})

    db.refresh(bill)
    assert bill.status.value == "cancelled"
    assert bill.is_paused is True
    assert result[0].color == "success"
    assert "cancelada" in result[0].children


def test_recurrence_action_rejects_cross_user(db, monkeypatch, sample_user):
    other_user = User(
        name="Outro Usuario",
        email="outro@email.com",
        password_hash="hashed_password",
        is_active=True,
        is_deleted=False,
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)
    bill = _create_monthly_bill(db, other_user.id)

    _patch_runtime(monkeypatch, db, user_id=sample_user.id)
    _patch_trigger(monkeypatch, "btn-pause-recurrence", bill.id)

    result = rec_callbacks.manage_recurrence_action([1], [], [], {"token": "ok"})

    db.refresh(bill)
    assert bill.is_paused is False
    assert result[0].color == "danger"
    assert "não encontrada" in result[0].children
    assert result[1] is True


def test_carregar_opcoes_recorrencia_popula_contas_e_categorias(
    db, monkeypatch, sample_user, sample_account, sample_category
):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)

    account_options, category_options = rec_callbacks.carregar_opcoes_recorrencia(
        True, "payable", {"token": "teste"}
    )

    assert {"label": "Conta Corrente", "value": sample_account.id} in account_options
    assert any(opt["value"] == sample_category.id for opt in category_options)


def test_carregar_opcoes_recorrencia_exclui_conta_cartao_e_respeita_tipo(
    db, monkeypatch, sample_user
):
    card_account = Account(
        user_id=sample_user.id,
        name="Nubank",
        account_type=AccountType.CREDIT_CARD,
        balance=Decimal("0"),
        initial_balance=Decimal("0"),
        is_active=True,
    )
    income_category = Category(
        user_id=sample_user.id,
        name="Salário",
        transaction_type=TransactionType.INCOME,
        is_system=False,
    )
    db.add_all([card_account, income_category])
    db.commit()
    db.refresh(card_account)
    db.refresh(income_category)

    _patch_runtime(monkeypatch, db, user_id=sample_user.id)

    account_options, category_options = rec_callbacks.carregar_opcoes_recorrencia(
        True, "receivable", {"token": "teste"}
    )

    assert all(opt["value"] != card_account.id for opt in account_options)
    assert any(opt["value"] == income_category.id for opt in category_options)


def test_carregar_opcoes_recorrencia_modal_fechado_nao_busca(db, monkeypatch, sample_user):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)

    result = rec_callbacks.carregar_opcoes_recorrencia(
        False, "payable", {"token": "teste"}
    )

    assert result == (no_update, no_update)
