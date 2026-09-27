"""
Repository para operações com categorias.
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.models.category import Category, TransactionType


class CategoryRepository:
    """
    Repository de categorias.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_categories_by_type(
        self, user_id: int, transaction_type: TransactionType
    ) -> list[Category]:
        """
        Busca categorias por tipo (sistema + usuário).
        """
        return (
            self.db.query(Category)
            .filter(
                Category.transaction_type == transaction_type,
                or_(Category.is_system, Category.user_id == user_id),
            )
            .order_by(Category.name)
            .all()
        )

    def get_all_user_categories(self, user_id: int) -> list[Category]:
        """
        Retorna todas as categorias do usuário (sistema + próprias).
        """
        return (
            self.db.query(Category)
            .filter(or_(Category.is_system, Category.user_id == user_id))
            .order_by(Category.transaction_type, Category.name)
            .all()
        )

    def get_by_id(self, category_id: int) -> Category | None:
        """
        Busca categoria por ID.
        """
        return self.db.query(Category).filter(Category.id == category_id).first()
