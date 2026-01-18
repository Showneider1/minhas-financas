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
# INICIALIZAÇÃO
# ===============================
app_logger.info(f"Inicializando {settings.APP_NAME} v{settings.APP_VERSION}")
app_logger.info(f"Ambiente: {settings.ENVIRONMENT}")
app_logger.info(f"Debug: {settings.DEBUG}")

# Inicializa banco (apenas em desenvolvimento)
if settings.ENVIRONMENT == "development":
    try:
        init_db()
        app_logger.info("Banco de dados inicializado")
        
        # Seed de categorias padrão
        from database.connection import get_db_session
        from services.category_service import CategoryService
        
        with get_db_session() as db:
            category_service = CategoryService(db)
            category_service.seed_default_categories()
            app_logger.info("Categorias padrão criadas")
    
    except Exception as e:
        app_logger.error(f"Erro ao inicializar banco: {e}")

app_logger.info("Aplicação iniciada com sucesso")
