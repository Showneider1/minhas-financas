import sqlite3
from pathlib import Path

# Usa o mesmo caminho do settings
db_path = Path("data/finance.db")  # ← CORRIGIDO (estava database.db)

if not db_path.exists():
    print(f"❌ Banco não encontrado: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Verifica transações
cursor.execute('SELECT id, description, base_amount, transaction_type, due_date, paid_date, user_id FROM transactions')
transactions = cursor.fetchall()

print(f"\n📂 Banco: {db_path.absolute()}")
print(f"📊 Total de transações: {len(transactions)}\n")

if transactions:
    for t in transactions:
        print(f"ID: {t[0]} | {t[1]} | R$ {t[2]} | Tipo: {t[3]} | Vencimento: {t[4]} | Pago: {t[5]} | User: {t[6]}")
else:
    print("❌ Nenhuma transação encontrada!")

conn.close()
