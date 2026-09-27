"""
Repository base com operações CRUD genéricas.
"""

import logging
from typing import Any, Generic, TypeVar

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from database.base import Base

# TypeVar para generics
ModelType = TypeVar("ModelType", bound=Base)
logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelType]):
    """
    Repository base com operações CRUD padrão.
    Pode ser estendido por repositories específicos.
    """

    def __init__(self, model: type[ModelType], db: Session):
        """
        Args:
            model: Classe do model SQLAlchemy
            db: Sessão do banco
        """
        self.model = model
        self.db = db

    def create(self, **kwargs) -> ModelType:
        """
        Cria novo registro.
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance

    def get_by_id(self, id: int) -> ModelType | None:
        """Busca por ID (sem filtro de dono — NÃO usar para entidades owned)."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_owned(self, id: int, user_id: int) -> ModelType | None:
        """Busca por ID + dono. OBRIGATÓRIO para entidades com user_id (anti-IDOR).

        Retorna None se inexistente OU de outro usuário (não distinguir).
        """
        if not hasattr(self.model, "user_id"):
            raise TypeError(f"{self.model.__name__} não possui user_id — use get_by_id.")
        return (
            self.db.query(self.model)
            .filter(self.model.id == id, self.model.user_id == user_id)
            .first()
        )

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_desc: bool = False,
    ) -> list[ModelType]:
        """Lista todos os registros com paginação."""
        query = self.db.query(self.model)

        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            query = query.order_by(desc(order_field) if order_desc else asc(order_field))

        return query.offset(skip).limit(limit).all()

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Conta registros."""
        query = self.db.query(self.model)
        if filters:
            query = self._apply_filters(query, filters)
        return query.count()

    def update(self, id: int, **kwargs) -> ModelType | None:
        """
        Atualiza registro.

        Safety: Remove explicitamente 'id' dos kwargs para impedir
        alteração de chave primária acidental.
        """
        instance = self.get_by_id(id)
        if not instance:
            return None

        # Segurança: Imutabilidade da PK
        kwargs.pop("id", None)

        has_changes = False
        for key, value in kwargs.items():
            if hasattr(instance, key) and getattr(instance, key) != value:
                setattr(instance, key, value)
                has_changes = True

        if has_changes:
            self.db.flush()
            self.db.refresh(instance)

        return instance

    def update_owned(self, id: int, user_id: int, **kwargs) -> ModelType | None:
        """Atualiza registro apenas se pertencer ao usuário (anti-IDOR)."""
        instance = self.get_owned(id, user_id)
        if not instance:
            return None
        kwargs.pop("id", None)
        kwargs.pop("user_id", None)
        has_changes = False
        for key, value in kwargs.items():
            if hasattr(instance, key) and getattr(instance, key) != value:
                setattr(instance, key, value)
                has_changes = True
        if has_changes:
            self.db.flush()
            self.db.refresh(instance)
        return instance

    def delete(self, id: int) -> bool:
        """Deleta registro permanentemente."""
        instance = self.get_by_id(id)
        if not instance:
            return False

        self.db.delete(instance)
        self.db.flush()
        return True

    def delete_owned(self, id: int, user_id: int) -> bool:
        """Deleta apenas se pertencer ao usuário (anti-IDOR)."""
        instance = self.get_owned(id, user_id)
        if not instance:
            return False
        self.db.delete(instance)
        self.db.flush()
        return True

    def soft_delete(self, id: int) -> bool:
        """Soft delete (exclusão lógica)."""
        instance = self.get_by_id(id)
        if not instance:
            return False

        if hasattr(instance, "soft_delete"):
            instance.soft_delete()  # Assume que o model tem esse método ou use um campo
            self.db.flush()
            return True

        logger.warning(f"Tentativa de soft_delete em modelo {self.model.__name__} sem suporte.")
        return False

    def restore(self, id: int) -> bool:
        """Restaura registro com soft delete."""
        instance = self.get_by_id(id)
        if not instance:
            return False

        if hasattr(instance, "restore"):
            instance.restore()
            self.db.flush()
            return True

        return False

    def exists(self, id: int) -> bool:
        """Verifica se registro existe de forma otimizada."""
        return self.db.query(self.model.id).filter(self.model.id == id).first() is not None

    def _apply_filters(self, query, filters: dict[str, Any]):
        """Aplica filtros à query."""
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        return query
