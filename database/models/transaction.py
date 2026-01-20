"""
Modelo de Transação.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum, Boolean
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
    Modelo de Transação Financeira.
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    base_amount = Column(Float, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    
    # Datas - Robustez para Cartão de Crédito
    purchase_date = Column(Date, nullable=False, index=True) # Data da Compra (passou o cartão)
    due_date = Column(Date, nullable=False, index=True)      # Data do Vencimento (fatura ou boleto)
    paid_date = Column(Date, nullable=True, index=True)      # Data da Efetivação (saiu dinheiro da conta)
    
    # Status como Coluna Real (Corrige o erro de atributo e melhora performance)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, index=True)
    
    # Parcelamento e Recorrência
    is_recurring = Column(Boolean, default=False)   # Assinatura?
    installment_number = Column(Integer, default=1) # Parcela 1
    total_installments = Column(Integer, default=1) # De 12
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    
    # Metadata
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")