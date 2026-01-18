"""
Repository base com operações CRUD genéricas.
"""
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from database.base import Base

# TypeVar para generics
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Repository base com operações CRUD padrão.
    Pode ser estendido por repositories específicos.
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
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
        
        Args:
            **kwargs: Campos do model
        
        Returns:
            Instância criada
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Busca por ID.
        
        Args:
            id: ID do registro
        
        Returns:
            Instância ou None
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> List[ModelType]:
        """
        Lista todos os registros com paginação.
        
        Args:
            skip: Número de registros a pular
            limit: Limite de registros
            order_by: Campo para ordenação
            order_desc: Ordenação descendente
        
        Returns:
            Lista de instâncias
        """
        query = self.db.query(self.model)
        
        # Ordenação
        if order_by:
            order_field = getattr(self.model, order_by, None)
            if order_field is not None:
                query = query.order_by(desc(order_field) if order_desc else asc(order_field))
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Conta registros.
        
        Args:
            filters: Filtros a aplicar
        
        Returns:
            Número de registros
        """
        query = self.db.query(self.model)
        
        if filters:
            query = self._apply_filters(query, filters)
        
        return query.count()
    
    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        Atualiza registro.
        
        Args:
            id: ID do registro
            **kwargs: Campos a atualizar
        
        Returns:
            Instância atualizada ou None
        """
        instance = self.get_by_id(id)
        if not instance:
            return None
        
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        self.db.flush()
        self.db.refresh(instance)
        return instance
    
    def delete(self, id: int) -> bool:
        """
        Deleta registro permanentemente.
        
        Args:
            id: ID do registro
        
        Returns:
            True se deletado, False se não encontrado
        """
        instance = self.get_by_id(id)
        if not instance:
            return False
        
        self.db.delete(instance)
        self.db.flush()
        return True
    
    def soft_delete(self, id: int) -> bool:
        """
        Soft delete (exclusão lógica).
        
        Args:
            id: ID do registro
        
        Returns:
            True se deletado, False se não encontrado
        """
        instance = self.get_by_id(id)
        if not instance:
            return False
        
        if hasattr(instance, 'soft_delete'):
            instance.soft_delete()
            self.db.flush()
            return True
        
        return False
    
    def restore(self, id: int) -> bool:
        """
        Restaura registro com soft delete.
        
        Args:
            id: ID do registro
        
        Returns:
            True se restaurado
        """
        instance = self.get_by_id(id)
        if not instance:
            return False
        
        if hasattr(instance, 'restore'):
            instance.restore()
            self.db.flush()
            return True
        
        return False
    
    def exists(self, id: int) -> bool:
        """
        Verifica se registro existe.
        
        Args:
            id: ID do registro
        
        Returns:
            True se existe
        """
        return self.db.query(self.model.id).filter(self.model.id == id).first() is not None
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """
        Aplica filtros à query.
        
        Args:
            query: Query SQLAlchemy
            filters: Dicionário de filtros
        
        Returns:
            Query com filtros aplicados
        """
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.filter(getattr(self.model, field) == value)
        
        return query
