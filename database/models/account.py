"""
Model de conta bancária/financeira.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database.base import Base
from database.mixins import TimestampMixin, SoftDeleteMixin
import enum


class AccountType(str, enum.Enum):
    """Tipos de conta."""
    CHECKING = "checking"      # Conta corrente
    SAVINGS = "savings"        # Poupança
    INVESTMENT = "investment"  # Investimentos
    CREDIT_CARD = "credit_card" # Cartão de crédito
    CASH = "cash"              # Dinheiro
    OTHER = "other"            # Outras


class Account(Base, TimestampMixin, SoftDeleteMixin):
    """
    Conta financeira do usuário.
    """
    __tablename__ = "accounts"

    # Identificação
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    
    # Tipo e moeda
    account_type = Column(
        SQLEnum(AccountType), 
        default=AccountType.CHECKING, 
        nullable=False
    )
    currency = Column(String(3), default="BRL", nullable=False)
    
    # Saldo e Valores
    balance = Column(Float, default=0.0, nullable=False)
    initial_balance = Column(Float, default=0.0, nullable=False)
    
    # CAMPOS ESPECÍFICOS PARA CARTÃO DE CRÉDITO (Novos)
    credit_limit = Column(Float, default=0.0, nullable=True)     # Limite do cartão
    closing_day = Column(Integer, nullable=True)                 # Dia de fechamento da fatura (1-31)
    due_day = Column(Integer, nullable=True)                     # Dia de vencimento da fatura (1-31)
    
    # Visual
    color = Column(String(20), default="#2ecc71", nullable=False)
    icon = Column(String(50), default="bi-bank", nullable=True)  # Ícone do bootstrap
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relacionamentos
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", lazy="dynamic")
    goals           = relationship("Goal",          back_populates="account")
    scheduled_bills  = relationship("ScheduledBill", back_populates="account")
    
    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', type='{self.account_type}')>"
