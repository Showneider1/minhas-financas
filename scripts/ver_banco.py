from database.connection import engine
from sqlalchemy import inspect

def print_schema():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    print("="*40)
    print(f"🔍 ESTRUTURA DO BANCO DE DADOS")
    print("="*40)

    for table_name in table_names:
        print(f"\n📂 TABELA: {table_name.upper()}")
        print("-" * 30)
        
        # Colunas
        columns = inspector.get_columns(table_name)
        print("  COLUNAS:")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            pk = "🔑 PK" if col['primary_key'] else ""
            print(f"   - {col['name']:<15} | {str(col['type']):<10} | {nullable} {pk}")
        
        # Foreign Keys
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            print("  🔗 RELACIONAMENTOS (FK):")
            for fk in fks:
                print(f"   - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

if __name__ == "__main__":
    print_schema()