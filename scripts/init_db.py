"""
Cria banco de dados automaticamente usando SQLAlchemy (baseado nos models).
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from sqlalchemy import create_engine, text
from database.base import Base
from database.models.user import User
from database.models.account import Account
from database.models.category import Category
from database.models.transaction import Transaction
from database.connection import get_db_session

# Remove banco antigo
db_path = Path("data/finance.db")  # ← CORRIGIDO
if db_path.exists():
    print(f"🗑️  Removendo banco antigo: {db_path}")
    os.remove(db_path)

# Garante que pasta data existe
Path("data").mkdir(exist_ok=True)

print("=" * 60)
print("🚀 CRIANDO BANCO DE DADOS (SQLALCHEMY)")
print("=" * 60)

# Cria engine
DATABASE_URL = "sqlite:///./data/finance.db"  # ← CORRIGIDO
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Cria todas as tabelas automaticamente
print("\n🔧 Criando tabelas a partir dos models...\n")
Base.metadata.create_all(bind=engine)

print("  ✓ users")
print("  ✓ accounts")
print("  ✓ categories")
print("  ✓ transactions")

# Seed de categorias
print("\n📁 Inserindo categorias padrão...\n")

categories = [
    # Despesas
    ("Alimentação", "EXPENSE", "🍔", "#e74c3c"),
    ("Transporte", "EXPENSE", "🚗", "#3498db"),
    ("Moradia", "EXPENSE", "🏠", "#9b59b6"),
    ("Saúde", "EXPENSE", "💊", "#1abc9c"),
    ("Educação", "EXPENSE", "📚", "#f39c12"),
    ("Lazer", "EXPENSE", "🎮", "#e67e22"),
    ("Outros", "EXPENSE", "📦", "#95a5a6"),
    
    # Receitas
    ("Salário", "INCOME", "💰", "#27ae60"),
    ("Freelance", "INCOME", "💻", "#2ecc71"),
    ("Investimentos", "INCOME", "📈", "#16a085"),
    ("Outros", "INCOME", "💵", "#27ae60"),
]

with get_db_session() as db:
    for name, type_, icon, color in categories:
        db.execute(
            text("""
                INSERT INTO categories (name, transaction_type, icon, color, is_system, user_id, parent_id)
                VALUES (:name, :type, :icon, :color, 1, NULL, NULL)
            """),
            {"name": name, "type": type_, "icon": icon, "color": color}
        )
        print(f"  ✓ {icon} {name}")

print("\n" + "=" * 60)
print("✅ BANCO CRIADO COM SUCESSO!")
print("=" * 60)

# Verifica arquivo
if db_path.exists():
    size = db_path.stat().st_size
    print(f"\n📂 Localização: {db_path.absolute()}")
    print(f"📊 Tamanho: {size:,} bytes")
    print(f"✅ Arquivo criado com sucesso!")
else:
    print("\n❌ Erro: Arquivo não foi criado!")

print("\n▶️  Execute: python myindex.py")
