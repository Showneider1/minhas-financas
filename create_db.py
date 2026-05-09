"""
Script utilitário para RESET e SEED do banco de dados em desenvolvimento.

⚠️  ATENÇÃO: Este script APAGA TODOS OS DADOS existentes e recria o banco do zero.
    Nunca importe ou execute em produção.
    Use a variável de ambiente DEMO_USER_PASSWORD para definir a senha do usuário demo.
"""
import os
from database.connection import engine, SessionLocal
from database.base import Base
import database.models  # Registra todos os models no metadata
from database.models.category import Category, TransactionType
from database.models.account import Account, AccountType
from database.models.user import User
from werkzeug.security import generate_password_hash


# ──────────────────────────────────────────────────────────────
# BUG 1 CORRIGIDO: função renomeada para "reset_and_seed_db"
# para deixar explícito que ela DESTRÓI dados. Nunca deve ter
# o mesmo nome que a função segura init_db() de connection.py.
# ──────────────────────────────────────────────────────────────
def reset_and_seed_db():
    """
    Recria o banco do zero e insere dados de demonstração.
    EXCLUSIVO PARA DESENVOLVIMENTO / TESTES.
    """
    print("⏳ Iniciando RESET completo do Banco de Dados...")

    # 1. DROP + CREATE de todas as tabelas
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas recriadas com sucesso!")

    db = SessionLocal()

    try:
        # 2. Criar Usuário Demo
        # ──────────────────────────────────────────────────────
        # BUG 9 CORRIGIDO: senha lida de variável de ambiente.
        # Defina DEMO_USER_PASSWORD no .env para alterar o padrão.
        # ──────────────────────────────────────────────────────
        demo_password = os.environ.get("DEMO_USER_PASSWORD", "Demo@2024!")
        demo_email    = os.environ.get("DEMO_USER_EMAIL",    "demo@minhasfinancas.local")

        print(f"👤 Criando usuário demo: {demo_email}")
        user = User(
            name="Usuário Demo",
            email=demo_email,
            password_hash=generate_password_hash(demo_password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 3. Criar Contas Padrão
        print("🏦 Criando contas bancárias...")
        contas = [
            Account(name="Carteira",         account_type=AccountType.CASH,        user_id=user.id, balance=0, color="#2ecc71"),
            Account(name="Nubank",           account_type=AccountType.CHECKING,    user_id=user.id, balance=0, color="#8e44ad"),
            Account(name="Itaú Cartão",      account_type=AccountType.CREDIT_CARD, user_id=user.id, balance=0, closing_day=25, due_day=5, color="#e67e22"),
            Account(name="XP Investimentos", account_type=AccountType.INVESTMENT,  user_id=user.id, balance=0, color="#f1c40f"),
        ]
        db.add_all(contas)

        # 4. Criar Categorias Padrão
        print("📂 Criando categorias...")
        categorias = [
            # Receitas
            {"name": "Salário",         "type": TransactionType.INCOME,   "icon": "💰", "color": "#27ae60"},
            {"name": "Dividendos",      "type": TransactionType.INCOME,   "icon": "📈", "color": "#2ecc71"},
            {"name": "Outras Receitas", "type": TransactionType.INCOME,   "icon": "➕", "color": "#16a085"},
            # Despesas
            {"name": "Alimentação",     "type": TransactionType.EXPENSE,  "icon": "🍔", "color": "#e74c3c"},
            {"name": "Moradia",         "type": TransactionType.EXPENSE,  "icon": "🏠", "color": "#c0392b"},
            {"name": "Transporte",      "type": TransactionType.EXPENSE,  "icon": "🚗", "color": "#e67e22"},
            {"name": "Lazer",           "type": TransactionType.EXPENSE,  "icon": "🎉", "color": "#f1c40f"},
            {"name": "Saúde",           "type": TransactionType.EXPENSE,  "icon": "💊", "color": "#8e44ad"},
            {"name": "Educação",        "type": TransactionType.EXPENSE,  "icon": "📚", "color": "#2980b9"},
            {"name": "Compras",         "type": TransactionType.EXPENSE,  "icon": "🛍️", "color": "#9b59b6"},
            # Transferências
            {"name": "Transferência",   "type": TransactionType.TRANSFER, "icon": "↔️", "color": "#95a5a6"},
        ]

        for cat in categorias:
            db_cat = Category(
                name=cat["name"],
                transaction_type=cat["type"],
                icon=cat["icon"],
                color=cat["color"],
                user_id=user.id,
                is_system=True,
            )
            db.add(db_cat)

        db.commit()
        print("✅ Banco de dados populado com sucesso!")
        print(f"\n🔑 Credenciais demo:")
        print(f"   Email: {demo_email}")
        print(f"   Senha: {demo_password}")

    except Exception as e:
        print(f"❌ Erro ao popular banco: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_and_seed_db()
