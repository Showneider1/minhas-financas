"""Enums unificados — fonte única sem regressão (Missão P1 Fase 2/4).

Garante: identidade entre models/schemas/services, mapeamento VARCHAR
(SQLite e futuro Postgres), e que as rotas de API (services) aceitam
valores crus sem quebrar.
"""
from datetime import date
from decimal import Decimal

import database.enums as central
from database.enums import TransactionType, TransactionStatus


def test_single_source_identity():
    from database.models.category import TransactionType as M1
    from database.models.transaction import TransactionType as M2, TransactionStatus as S2
    from schemas.transaction_schema import TransactionType as Sc1, TransactionStatus as Sc2

    assert central.TransactionType is M1 is M2 is Sc1
    assert central.TransactionStatus is S2 is Sc2
    assert M1.EXPENSE == "EXPENSE"  # str-enum compara com string crua


def test_varchar_mapping_for_postgres():
    from database.models.transaction import Transaction

    assert Transaction.__table__.c.transaction_type.type.native_enum is False
    assert Transaction.__table__.c.status.type.native_enum is False


def test_schema_accepts_raw_strings_and_coerces():
    from schemas.transaction_schema import TransactionCreate

    payload = TransactionCreate(
        description="Salário mensal",
        base_amount=Decimal("1000.00"),
        transaction_type="INCOME",  # string crua (como chega do frontend)
        category_id=1,
        account_id=1,
        purchase_date=date(2026, 1, 5),
        due_date=date(2026, 1, 5),
        paid_date=date(2026, 1, 5),
    )
    assert payload.transaction_type is TransactionType.INCOME


def test_service_layer_no_regression(db, sample_user, sample_account):
    """Criar via schema com string crua funciona de ponta a ponta."""
    from database.models.category import Category
    from schemas.transaction_schema import TransactionCreate
    from services.finance_service import FinanceService

    cat = Category(user_id=sample_user.id, name="Salário",
                   transaction_type=TransactionType.INCOME, is_system=False)
    db.add(cat)
    db.commit()

    tx = FinanceService(db).create_transaction(
        user_id=sample_user.id,
        transaction_data=TransactionCreate(
            description="Salário mensal",
            base_amount=Decimal("2500.00"),
            transaction_type="INCOME",
            category_id=cat.id,
            account_id=sample_account.id,
            purchase_date=date(2026, 1, 5),
            due_date=date(2026, 1, 5),
            paid_date=date(2026, 1, 5),
        ),
    )
    assert tx.transaction_type == TransactionType.INCOME
    assert tx.status == TransactionStatus.PAID
