"""
Script de Migração Manual (Manutenção Completa).
Sincroniza o banco de dados com as últimas alterações de Modelagem.
"""
import sys
import os
import logging

# Configuração básica de log para o script
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_migration")

# Adiciona raiz ao path
sys.path.append(os.getcwd())

from sqlalchemy import text, inspect
from database.connection import engine

def add_column_if_not_exists(conn, table_name, column_name, column_type):
    """Adiciona coluna se ela não existir."""
    inspector = inspect(conn)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    
    if column_name not in columns:
        logger.info(f"🛠️  Adicionando '{column_name}' em '{table_name}'...")
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
        return True
    return False

def upgrade_database():
    logger.info("🔄 Iniciando atualização do Schema do Banco de Dados...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Atualizações na tabela ACCOUNTS (Cartão de Crédito)
            # -----------------------------------------------------
            add_column_if_not_exists(conn, 'accounts', 'credit_limit', 'FLOAT DEFAULT 0.0')
            add_column_if_not_exists(conn, 'accounts', 'closing_day', 'INTEGER')
            add_column_if_not_exists(conn, 'accounts', 'due_day', 'INTEGER')
            add_column_if_not_exists(conn, 'accounts', 'icon', "VARCHAR(50) DEFAULT 'bi-bank'")
            add_column_if_not_exists(conn, 'accounts', 'color', "VARCHAR(20) DEFAULT '#2ecc71'")

            # 2. Atualizações na tabela TRANSACTIONS (Regras de Negócio)
            # ----------------------------------------------------------
            # Novos campos financeiros
            cols_added = []
            cols_added.append(add_column_if_not_exists(conn, 'transactions', 'amount', 'FLOAT DEFAULT 0.0'))
            cols_added.append(add_column_if_not_exists(conn, 'transactions', 'interest', 'FLOAT DEFAULT 0.0'))
            cols_added.append(add_column_if_not_exists(conn, 'transactions', 'discount', 'FLOAT DEFAULT 0.0'))
            cols_added.append(add_column_if_not_exists(conn, 'transactions', 'cashback', 'FLOAT DEFAULT 0.0'))
            
            # Campos informativos/controle
            add_column_if_not_exists(conn, 'transactions', 'notes', 'VARCHAR(500)')
            add_column_if_not_exists(conn, 'transactions', 'is_recurring', 'BOOLEAN DEFAULT 0')

            # 3. Migração de Dados (Data Fix)
            # ----------------------------------------------------------
            # Se adicionamos a coluna 'amount', ela estará zerada. 
            # Devemos copiar o valor de 'base_amount' para 'amount' para manter consistência.
            if any(cols_added):
                logger.info("💾 Migrando dados antigos: copiando base_amount para amount...")
                conn.execute(text("UPDATE transactions SET amount = base_amount WHERE amount = 0 OR amount IS NULL"))

            trans.commit()
            logger.info("\n🚀 Banco de dados atualizado com sucesso!")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"\n❌ Erro crítico na migração: {e}")
            raise e

if __name__ == "__main__":
    upgrade_database()