from database.connection import engine, SessionLocal
from database.base import Base
# Importa o __init__ para registrar todos os models
import database.models 
from database.models.category import Category, TransactionType
from database.models.account import Account, AccountType
from database.models.user import User
from werkzeug.security import generate_password_hash

def init_db():
    print("⏳ Iniciando recriação do Banco de Dados...")
    
    # 1. DROP e CREATE de todas as tabelas
    # CUIDADO: Isso apaga todos os dados existentes!
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas recriadas com sucesso!")

    db = SessionLocal()

    try:
        # 2. Criar Usuário Padrão
        print("👤 Criando usuário padrão...")
        user = User(
            name="Usuario Demo",
            email="email@demo.com",
            password_hash=generate_password_hash("123456") 
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # 3. Criar Contas Padrão
        print("🏦 Criando contas bancárias...")
        contas = [
            Account(name="Carteira", account_type=AccountType.CASH, user_id=user.id, balance=0, color="#2ecc71"),
            Account(name="Nubank", account_type=AccountType.CHECKING, user_id=user.id, balance=0, color="#8e44ad"),
            Account(name="Itaú Cartão", account_type=AccountType.CREDIT_CARD, user_id=user.id, balance=0, closing_day=25, due_day=5, color="#e67e22"),
            Account(name="XP Investimentos", account_type=AccountType.INVESTMENT, user_id=user.id, balance=0, color="#f1c40f"),
        ]
        db.add_all(contas)
        
        # 4. Criar Categorias Padrão
        print("📂 Criando categorias...")
        categorias = [
            # Receitas
            {"name": "Salário", "type": TransactionType.INCOME, "icon": "💰", "color": "#27ae60"},
            {"name": "Dividendos", "type": TransactionType.INCOME, "icon": "📈", "color": "#2ecc71"},
            {"name": "Outras Receitas", "type": TransactionType.INCOME, "icon": "➕", "color": "#16a085"},
            
            # Despesas
            {"name": "Alimentação", "type": TransactionType.EXPENSE, "icon": "🍔", "color": "#e74c3c"},
            {"name": "Moradia", "type": TransactionType.EXPENSE, "icon": "🏠", "color": "#c0392b"},
            {"name": "Transporte", "type": TransactionType.EXPENSE, "icon": "🚗", "color": "#e67e22"},
            {"name": "Lazer", "type": TransactionType.EXPENSE, "icon": "🎉", "color": "#f1c40f"},
            {"name": "Saúde", "type": TransactionType.EXPENSE, "icon": "💊", "color": "#8e44ad"},
            {"name": "Educação", "type": TransactionType.EXPENSE, "icon": "📚", "color": "#2980b9"},
            {"name": "Compras", "type": TransactionType.EXPENSE, "icon": "🛍️", "color": "#9b59b6"},
            
            # Transferências
            {"name": "Transferência", "type": TransactionType.TRANSFER, "icon": "↔️", "color": "#95a5a6"},
        ]

        for cat in categorias:
            db_cat = Category(
                name=cat["name"],
                transaction_type=cat["type"],
                icon=cat["icon"],
                color=cat["color"],
                user_id=user.id,
                is_system=True
            )
            db.add(db_cat)

        db.commit()
        print("✅ Banco de dados populado com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao popular banco: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()