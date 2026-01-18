"""
Modelo de Categoria com suporte a subcategorias.
"""
from sqlalchemy import Column, Integer, String, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database.base import Base
import enum


class TransactionType(enum.Enum):
    """Tipo de transação."""
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class Category(Base):
    """
    Modelo de Categoria com hierarquia (categoria > subcategoria).
    """
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=True)  # Agora nullable
    icon = Column(String(10), default="📁")
    color = Column(String(20), default="#3498db")
    is_system = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Hierarquia de categorias
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    
    # Subcategorias
    parent = relationship("Category", remote_side=[id], backref="subcategories")
