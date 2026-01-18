"""
Configuração de logging da aplicação.
"""
import logging
import sys
from pathlib import Path
from config.settings import settings

# Cria diretório de logs se não existir
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# ===============================
# FORMATTERS
# ===============================

DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# ===============================
# APP LOGGER
# ===============================

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """
    Configura logger com handlers de console e arquivo.
    
    Args:
        name: Nome do logger
        log_file: Arquivo de log
        level: Nível de log
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove handlers existentes
    logger.handlers = []
    
    # Handler de arquivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(DETAILED_FORMAT)
    file_handler.setFormatter(file_formatter)
    
    # Handler de console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(SIMPLE_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    # Adiciona handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Logger principal da aplicação
app_logger = setup_logger(
    name="app",
    log_file="logs/app.log",
    level=getattr(logging, settings.LOG_LEVEL),
)

# Logger de auditoria (sem console output)
audit_logger_instance = logging.getLogger("audit")
audit_logger_instance.setLevel(logging.INFO)
audit_handler = logging.FileHandler("logs/audit.log", encoding='utf-8')
audit_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
audit_logger_instance.addHandler(audit_handler)


class AuditLogger:
    """
    Logger especializado para auditoria de ações do usuário.
    """
    
    def __init__(self):
        self.logger = audit_logger_instance
    
    def log(self, action: str, user_id: int = None, details: dict = None):
        """
        Registra ação de auditoria.
        
        Args:
            action: Ação realizada (ex: "user.login")
            user_id: ID do usuário
            details: Detalhes adicionais
        """
        message = f"Action: {action}"
        if user_id:
            message += f" | User: {user_id}"
        if details:
            message += f" | Details: {details}"
        
        self.logger.info(message)
    
    def log_login(self, user_id: int, email: str, success: bool = True):
        """Registra tentativa de login."""
        action = "user.login.success" if success else "user.login.failed"
        self.log(action, user_id, {"email": email})
    
    def log_logout(self, user_id: int):
        """Registra logout."""
        self.log("user.logout", user_id)
    
    def log_create(self, resource_type: str, resource_id: int, user_id: int, details: dict = None):
        """Registra criação de recurso."""
        self.log(
            f"{resource_type}.create",
            user_id,
            {"resource_id": resource_id, **(details or {})}
        )
    
    def log_update(self, resource_type: str, resource_id: int, user_id: int, changes: dict):
        """Registra atualização de recurso."""
        self.log(
            f"{resource_type}.update",
            user_id,
            {"resource_id": resource_id, "changes": changes}
        )
    
    def log_delete(self, resource_type: str, resource_id: int, user_id: int):
        """Registra deleção de recurso."""
        self.log(
            f"{resource_type}.delete",
            user_id,
            {"resource_id": resource_id}
        )


# Instância global do audit logger
audit_logger = AuditLogger()
