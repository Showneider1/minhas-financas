"""
Sistema de auditoria de ações do usuário.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from config.settings import settings

# Logger de auditoria
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Handler de arquivo
if settings.AUDIT_ENABLED:
    handler = logging.FileHandler(settings.AUDIT_LOG_FILE, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)


class AuditLog:
    """
    Classe para registrar ações de auditoria.
    """
    
    @staticmethod
    def log_action(action: str, user_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        """
        Registra uma ação de auditoria.
        
        Args:
            action: Ação realizada
            user_id: ID do usuário
            details: Detalhes adicionais
        """
        if not settings.AUDIT_ENABLED:
            return
        
        message = f"Action: {action}"
        if user_id:
            message += f" | User: {user_id}"
        if details:
            message += f" | Details: {details}"
        
        audit_logger.info(message)
    
    @staticmethod
    def log_login(user_id: int, email: str, success: bool = True):
        """Registra tentativa de login."""
        action = "user.login.success" if success else "user.login.failed"
        AuditLog.log_action(action, user_id, {"email": email})
    
    @staticmethod
    def log_logout(user_id: int):
        """Registra logout."""
        AuditLog.log_action("user.logout", user_id)
    
    @staticmethod
    def log_create(resource_type: str, resource_id: int, user_id: int, details: Dict = None):
        """Registra criação de recurso."""
        AuditLog.log_action(
            f"{resource_type}.create",
            user_id,
            {"resource_id": resource_id, **(details or {})}
        )
    
    @staticmethod
    def log_update(resource_type: str, resource_id: int, user_id: int, changes: Dict):
        """Registra atualização de recurso."""
        AuditLog.log_action(
            f"{resource_type}.update",
            user_id,
            {"resource_id": resource_id, "changes": changes}
        )
    
    @staticmethod
    def log_delete(resource_type: str, resource_id: int, user_id: int):
        """Registra deleção de recurso."""
        AuditLog.log_action(
            f"{resource_type}.delete",
            user_id,
            {"resource_id": resource_id}
        )


# Instância global para importação
audit_log = AuditLog()
