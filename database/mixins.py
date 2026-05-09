"""
Mixins para models SQLAlchemy com funcionalidades comuns.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declared_attr


class TimestampMixin:
    """
    Adiciona campos de timestamp automáticos.
    """
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )


class SoftDeleteMixin:
    """
    Implementa soft delete (exclusão lógica).
    """
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def soft_delete(self):
        """Marca registro como deletado."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restaura registro deletado."""
        self.is_deleted = False
        self.deleted_at = None


class UserTrackingMixin:
    """
    Rastreia qual usuário criou/modificou o registro.
    """
    @declared_attr
    def created_by_id(cls):
        return Column(Integer, nullable=True)

    @declared_attr
    def updated_by_id(cls):
        return Column(Integer, nullable=True)
