"""
Modelo de Transação.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database.base import Base
from database.models.category import TransactionType
import enum


class TransactionStatus(enum.Enum):
    """Status da transação."""
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class Transaction(Base):
    """
    Modelo de Transação.
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    base_amount = Column(Float, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    
    @property
    def status(self) -> TransactionStatus:
        """Retorna status baseado na paid_date."""
        if self.paid_date:
            return TransactionStatus.PAID
        return TransactionStatus.PENDING
