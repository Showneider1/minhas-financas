"""
Modelo de Metas (Budget).
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from database.base import Base
from datetime import datetime

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    amount = Column(Float, nullable=False)  # Valor limite
    
    # Controle Temporal (Meta Mensal)
    month = Column(Integer, nullable=False) # 1 a 12
    year = Column(Integer, nullable=False)  # Ex: 2026
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    user = relationship("User")
    category = relationship("Category")

    # Garante que só existe UMA meta para a mesma categoria no mesmo mês
    __table_args__ = (
        UniqueConstraint('user_id', 'category_id', 'month', 'year', name='unique_budget_per_month'),
    )