"""
Repository para operações com categorias.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models.category import Category, TransactionType


class CategoryRepository:
    """
    Repository de categorias.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_categories_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType
    ) -> List[Category]:
        """
        Busca categorias por tipo (sistema + usuário).
        """
        return self.db.query(Category).filter(
            Category.transaction_type == transaction_type,
            (
                (Category.is_system == True) |
                (Category.user_id == user_id)
            )
        ).order_by(Category.name).all()
    
    def get_all_user_categories(self, user_id: int) -> List[Category]:
        """
        Retorna todas as categorias do usuário (sistema + próprias).
        """
        return self.db.query(Category).filter(
            (Category.is_system == True) |
            (Category.user_id == user_id)
        ).order_by(
            Category.transaction_type,
            Category.name
        ).all()
    
    def get_by_id(self, category_id: int) -> Optional[Category]:
        """
        Busca categoria por ID.
        """
        return self.db.query(Category).filter(Category.id == category_id).first()
