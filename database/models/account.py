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
    CHECKING = "checking"  # Conta corrente
    SAVINGS = "savings"    # Poupança
    INVESTMENT = "investment"  # Investimentos
    CREDIT_CARD = "credit_card"  # Cartão de crédito
    CASH = "cash"  # Dinheiro
    OTHER = "other"  # Outras


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
    currency = Column(String(3), default="BRL", nullable=False)  # ISO 4217
    
    # Saldo
    balance = Column(Float, default=0.0, nullable=False)
    initial_balance = Column(Float, default=0.0, nullable=False)
    
    # Cor para UI
    color = Column(String(20), default="#2ecc71", nullable=False)  # ← ADICIONAR
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relacionamentos
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", lazy="dynamic")
    
    # Propriedade para compatibilidade com código antigo
    @property
    def current_balance(self):
        """Alias para balance."""
        return self.balance
    
    @current_balance.setter
    def current_balance(self, value):
        """Setter para balance."""
        self.balance = value
    
    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', balance={self.balance})>"
    
    def update_balance(self, amount: float):
        """Atualiza saldo da conta."""
        self.balance += amount
