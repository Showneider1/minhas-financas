"""
Modelo de Categoria com suporte a subcategorias.
"""
from sqlalchemy import Column, Integer, String, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database.base import Base
import enum


class TransactionType(enum.Enum):
    INCOME   = "INCOME"
    EXPENSE  = "EXPENSE"
    TRANSFER = "TRANSFER"


class Category(Base):
    __tablename__ = "categories"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(100), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=True)
    icon             = Column(String(10),  default="📁")
    color            = Column(String(20),  default="#3498db")

    is_system = Column(Boolean, default=False)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    user            = relationship("User",          back_populates="categories")
    transactions    = relationship("Transaction",   back_populates="category")
    scheduled_bills = relationship("ScheduledBill", back_populates="category")

    parent = relationship("Category", remote_side=[id], backref="subcategories")