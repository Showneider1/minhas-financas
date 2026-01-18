import sqlite3

conn = sqlite3.connect('data/finance.db')
cursor = conn.cursor()

# Lista todas as tabelas
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in cursor.fetchall()]

print('\n📊 TABELAS NO BANCO:\n')
print('Tabelas:', tables)

print('\n📊 REGISTROS POR TABELA:\n')

for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'{table}: {count} registros')
    
    if table == 'transactions' or 'transaction' in table.lower():
        print(f'\n   🔍 Primeiros registros de {table}:')
        cursor.execute(f'SELECT * FROM {table} LIMIT 3')
        for row in cursor.fetchall():
            print(f'      {row}')

conn.close()
