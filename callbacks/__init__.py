"""
Importa todos os callbacks para registrá-los no app.
"""

# Auth callbacks SEMPRE primeiro
try:
    import callbacks.auth_callbacks
    print("✓ Auth callbacks carregados")
except Exception as e:
    print(f"✗ Erro ao carregar auth_callbacks: {e}")

try:
    import callbacks.sidebar_callbacks
    print("✓ Sidebar callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso sidebar_callbacks: {e}")

try:
    import callbacks.config_callbacks
    print("✓ Config callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso config_callbacks: {e}")

try:
    import callbacks.dashboard_callbacks
    print("✓ Dashboard callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso dashboard_callbacks: {e}")

try:
    import callbacks.extrato_callbacks
    print("✓ Extrato callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso extrato_callbacks: {e}")

try:
    import callbacks.transactions_callbacks
    print("✓ Transactions callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso transactions_callbacks: {e}")

try:
    import callbacks.account_callbacks
    print("✓ Account callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso account_callbacks: {e}")

try:
    import callbacks.category_callbacks
    print("✓ Category callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso category_callbacks: {e}")

try:
    import callbacks.export_callbacks
    print("✓ Export callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso export_callbacks: {e}")

print("\n📊 Callbacks registrados com sucesso!\n")

try:
    import callbacks.budget_callbacks
    print("✓ Budget callbacks carregados")
except Exception as e:
    print(f"⚠ Aviso budget_callbacks: {e}")

# ── Metas Financeiras ──────────────────────────────────────────────
try:
    import callbacks.goal_callbacks  # noqa: F401
    print("✓ Goal callbacks carregados")
except Exception as _e:
    print(f"⚠ Aviso goal_callbacks: {_e}")
