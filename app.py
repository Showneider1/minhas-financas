"""
Inicialização do aplicativo Dash.
"""
import dash
import dash_bootstrap_components as dbc
from config.settings import settings
from config.logging_config import app_logger
from database.connection import init_db

# ===============================
# ESTILOS EXTERNOS
# ===============================
external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css",
    "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap",
]

# ===============================
# CRIAÇÃO DO APP
# ===============================
app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
    title=settings.APP_NAME,
    update_title="Carregando...",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)

server = app.server


# ===============================
# INICIALIZAÇÃO CONTROLADA
# ===============================
def initialize_application():
    """
    Executa rotinas de inicialização como criação de banco e seeds.
    Deve ser idempotente — seguro de chamar múltiplas vezes sem efeitos colaterais.
    """
    app_logger.info(f"Inicializando {settings.APP_NAME} v{settings.APP_VERSION}")
    app_logger.info(f"Ambiente: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")

    try:
        # init_db() usa apenas create_all (seguro — não apaga dados existentes)
        init_db()

        # Seed de categorias padrão (idempotente — verifica existência antes de inserir)
        from database.connection import get_db_session
        from services.category_service import CategoryService

        with get_db_session() as db:
            try:
                category_service = CategoryService(db)
                category_service.seed_default_categories()
                app_logger.info("Categorias verificadas/criadas")
            except Exception as e:
                app_logger.error(f"Erro ao executar seed de categorias: {e}")

    except Exception as e:
        app_logger.error(f"Erro crítico na inicialização: {e}")


# ──────────────────────────────────────────────────────────────────
# BUG 2 CORRIGIDO: initialize_application() é chamada APENAS quando
# este módulo é o entry-point direto (__name__ == "__main__").
#
# Antes: `if __name__ == "__main__" or settings.ENVIRONMENT == "development"`
#   → executava a init a cada import do módulo em dev, causando
#     race conditions com múltiplos workers do Gunicorn.
#
# Agora: a condição de ENVIRONMENT foi removida daqui.
#   Em produção/staging, o Gunicorn deve chamar initialize_application()
#   via hook `post_fork` ou via script de entrypoint separado.
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    initialize_application()
else:
    app_logger.info("Aplicação carregada (módulo importado — init delegada ao entrypoint)")

app_logger.info("App Context pronto.")
