"""
Tratamento centralizado de erros.
"""
from typing import Dict, Any, Optional
from config.logging_config import app_logger
from utils.exceptions import AppException
from schemas.common import ErrorResponse
from datetime import datetime


def handle_error(error: Exception) -> Dict[str, Any]:
    """
    Processa erro e retorna response padronizado.
    
    Args:
        error: Exceção capturada
    
    Returns:
        Dict com erro formatado
    """
    # Erro customizado da aplicação
    if isinstance(error, AppException):
        app_logger.warning(
            f"AppException: {error.code} - {error.message}",
            extra={"details": error.details}
        )
        return error_response(
            error=error.message,
            code=error.code,
            status_code=error.status_code,
            details=error.details,
        )
    
    # Erro de validação Pydantic
    if hasattr(error, 'errors'):  # ValidationError do Pydantic
        validation_errors = []
        for err in error.errors():
            validation_errors.append({
                "field": ".".join(str(x) for x in err.get("loc", [])),
                "message": err.get("msg"),
                "type": err.get("type"),
            })
        
        app_logger.warning(f"Validation error: {validation_errors}")
        return error_response(
            error="Erro de validação",
            code="VALIDATION_ERROR",
            status_code=422,
            details={"errors": validation_errors},
        )
    
    # Erro genérico
    app_logger.error(f"Unhandled exception: {type(error).__name__} - {str(error)}", exc_info=True)
    return error_response(
        error="Erro interno do servidor",
        code="INTERNAL_ERROR",
        status_code=500,
    )


def error_response(
    error: str,
    code: str = "ERROR",
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cria response de erro padronizado.
    
    Args:
        error: Mensagem de erro
        code: Código do erro
        status_code: HTTP status code
        details: Detalhes adicionais
    
    Returns:
        Dict formatado
    """
    response = ErrorResponse(
        success=False,
        error=error,
        details=details or {},
        timestamp=datetime.utcnow(),
    )
    
    return {
        "success": False,
        "error": error,
        "code": code,
        "status_code": status_code,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat(),
    }


def success_response(
    message: str,
    data: Any = None,
) -> Dict[str, Any]:
    """
    Cria response de sucesso padronizado.
    
    Args:
        message: Mensagem de sucesso
        data: Dados a retornar
    
    Returns:
        Dict formatado
    """
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def safe_callback(func):
    """
    Decorator que envolve callback com tratamento de erros.
    
    Usage:
        @app.callback(...)
        @safe_callback
        def my_callback(...):
            # Se ocorrer erro, será tratado automaticamente
            pass
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return handle_error(e)
    
    return wrapper
