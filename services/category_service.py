"""
Serviço de categorias.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models.category import Category, TransactionType
from database.repositories.category_repo import CategoryRepository
from schemas.category_schema import CategoryCreate
from config.logging_config import app_logger


class CategoryService:
    """
    Serviço de gerenciamento de categorias.
    """

    def __init__(self, db: Session):
        self.db = db
        self.category_repo = CategoryRepository(db)

    def get_available_categories(
        self,
        user_id: int,
        transaction_type: TransactionType,
    ) -> List[Category]:
        """Retorna categorias disponíveis para o usuário (sistema + próprias)."""
        return self.category_repo.get_categories_by_type(user_id, transaction_type)

    def get_user_categories(self, user_id: int) -> List[Category]:
        """Retorna todas as categorias do usuário (sistema + próprias)."""
        return self.category_repo.get_all_user_categories(user_id)

    def create_user_category(self, user_id: int, data: CategoryCreate) -> Category:
        """Cria nova categoria personalizada do usuário."""
        category = Category(
            name=data.name,
            transaction_type=data.transaction_type,
            icon=data.icon or "📁",
            color=data.color or "#3498db",
            user_id=user_id,
            is_system=False,
        )
        self.db.add(category)
        self.db.flush()
        app_logger.info(f"Categoria criada: {category.id} - {category.name}")
        return category

    def seed_default_categories(self, user_id: Optional[int] = None):
        """
        Cria categorias padrão do sistema de forma idempotente.

        ──────────────────────────────────────────────────────────────
        BUG 4 CORRIGIDO: o parâmetro `user_id` agora é explícito e
        opcional (None = categoria global do sistema).

        Antes: o método não recebia user_id, tentava criar Categories
               sem o campo obrigatório → IntegrityError no banco.

        Agora: user_id é passado pelo chamador (app.py) quando
               pertinente, ou None para categorias globais de sistema.
               O model Category já permite user_id nullable.
        ──────────────────────────────────────────────────────────────
        """
        default_categories = [
            # Despesas
            {"name": "Alimentação", "type": TransactionType.EXPENSE,  "icon": "🍔", "color": "#e74c3c"},
            {"name": "Transporte",  "type": TransactionType.EXPENSE,  "icon": "🚗", "color": "#3498db"},
            {"name": "Moradia",     "type": TransactionType.EXPENSE,  "icon": "🏠", "color": "#9b59b6"},
            {"name": "Saúde",       "type": TransactionType.EXPENSE,  "icon": "💊", "color": "#1abc9c"},
            {"name": "Educação",    "type": TransactionType.EXPENSE,  "icon": "📚", "color": "#f39c12"},
            {"name": "Lazer",       "type": TransactionType.EXPENSE,  "icon": "🎮", "color": "#e67e22"},
            {"name": "Outros",      "type": TransactionType.EXPENSE,  "icon": "📦", "color": "#95a5a6"},
            # Receitas
            {"name": "Salário",      "type": TransactionType.INCOME,  "icon": "💰", "color": "#27ae60"},
            {"name": "Freelance",    "type": TransactionType.INCOME,  "icon": "💻", "color": "#2ecc71"},
            {"name": "Investimentos","type": TransactionType.INCOME,  "icon": "📈", "color": "#16a085"},
            {"name": "Outros",       "type": TransactionType.INCOME,  "icon": "💵", "color": "#27ae60"},
        ]

        created = 0
        for cat_data in default_categories:
            # Verifica se já existe (idempotente) — filtra por user_id correto
            query = self.db.query(Category).filter(
                Category.name == cat_data["name"],
                Category.transaction_type == cat_data["type"],
                Category.is_system == True,
            )
            if user_id is not None:
                query = query.filter(Category.user_id == user_id)
            else:
                query = query.filter(Category.user_id.is_(None))

            existing = query.first()
            if not existing:
                new_cat = Category(
                    name=cat_data["name"],
                    transaction_type=cat_data["type"],
                    icon=cat_data["icon"],
                    color=cat_data["color"],
                    user_id=user_id,   # None para categorias globais
                    is_system=True,
                )
                self.db.add(new_cat)
                created += 1

        if created:
            self.db.flush()
            app_logger.info(f"{created} categorias padrão criadas (user_id={user_id})")
        else:
            app_logger.info("Categorias padrão já existem — nenhuma ação necessária")
