"""
Modelo de Categoria com suporte a subcategorias.
"""

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database.base import Base
from database.enums import TransactionType  # canônico (P1) — re-export p/ compat

__all__ = ["Category", "TransactionType"]


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    transaction_type = Column(Enum(TransactionType, native_enum=False), nullable=True)
    # 40 chars: emoji + modificadores/ZWJ estouram VARCHAR(10) no Postgres.
    icon = Column(String(40), default="📁")
    color = Column(String(20), default="#3498db")

    is_system = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    scheduled_bills = relationship("ScheduledBill", back_populates="category")

    parent = relationship("Category", remote_side=[id], backref="subcategories")

    __table_args__ = (UniqueConstraint("name", "user_id", name="uq_category_name_user"),)
