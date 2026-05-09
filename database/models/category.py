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
    TRANSFER = "TRANSFER" # Adicionado suporte a transferências

class Category(Base):
    """
    Modelo de Categoria com hierarquia.
    """
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=True)
    icon = Column(String(10), default="📁")
    color = Column(String(20), default="#3498db")
    
    is_system = Column(Boolean, default=False) # Categorias padrão do sistema
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Hierarquia (Subcategorias)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
        scheduled_bills = relationship("ScheduledBill", back_populates="category")
    
    # Auto-relacionamento
    parent = relationship("Category", remote_side=[id], backref="subcategories")
