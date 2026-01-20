"""
Schemas Pydantic para Validação e Serialização de Transações.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from database.models.transaction import TransactionType, TransactionStatus

# ==========================================
# 1. BASE: Campos Comuns
# ==========================================
class TransactionBase(BaseModel):
    """
    Campos base compartilhados entre Criação e Leitura.
    """
    description: str = Field(
        ..., 
        min_length=3, 
        max_length=255, 
        description="Descrição curta da transação (ex: Mercado, Salário)"
    )
    base_amount: float = Field(
        ..., 
        gt=0, 
        description="Valor absoluto da transação. Deve ser positivo."
    )
    transaction_type: TransactionType = Field(
        ..., 
        description="Tipo: INCOME (Receita), EXPENSE (Despesa) ou TRANSFER (Transferência)"
    )
    
    # Chaves Estrangeiras
    category_id: int = Field(..., description="ID da categoria associada")
    account_id: int = Field(..., description="ID da conta bancária associada")
    
    # --- NOVOS CAMPOS DE ROBUSTEZ (CARTÃO & PRAZOS) ---
    purchase_date: date = Field(
        ..., 
        description="Data da competência/compra (Quando o fato ocorreu)"
    )
    due_date: date = Field(
        ..., 
        description="Data de vencimento (Quando deve ser pago)"
    )
    paid_date: Optional[date] = Field(
        None, 
        description="Data da liquidação (Quando o dinheiro saiu). Se null, está Pendente."
    )
    
    # --- NOVOS CAMPOS DE PARCELAMENTO & RECORRÊNCIA ---
    is_recurring: bool = Field(
        False, 
        description="Indica se é uma assinatura recorrente (ex: Netflix)"
    )
    installment_number: int = Field(
        1, 
        ge=1, 
        description="Número da parcela atual (ex: 1)"
    )
    total_installments: int = Field(
        1, 
        ge=1, 
        description="Total de parcelas (ex: 12)"
    )
    
    notes: Optional[str] = Field(
        None, 
        max_length=500, 
        description="Observações ou detalhes extras"
    )

    # --- VALIDAÇÕES DE LÓGICA DE NEGÓCIO ---
    @validator('installment_number')
    def validate_installment_logic(cls, v, values):
        """Garante que a parcela atual não seja maior que o total."""
        total = values.get('total_installments')
        if total and v > total:
            raise ValueError(f'Parcela atual ({v}) não pode ser maior que o total ({total})')
        return v

# ==========================================
# 2. CREATE: Para criar novas
# ==========================================
class TransactionCreate(TransactionBase):
    """
    Schema usado no POST /transactions.
    Herda tudo de Base, pois todos os campos são necessários ou têm default.
    """
    pass

# ==========================================
# 3. UPDATE: Para editar (Tudo Opcional)
# ==========================================
class TransactionUpdate(BaseModel):
    """
    Schema usado no PUT/PATCH. Todos os campos são opcionais.
    Isso permite atualizar apenas a 'description' sem enviar o 'amount' de novo.
    """
    description: Optional[str] = Field(None, min_length=3, max_length=255)
    base_amount: Optional[float] = Field(None, gt=0)
    transaction_type: Optional[TransactionType] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    
    # Datas
    purchase_date: Optional[date] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    
    # Detalhes
    is_recurring: Optional[bool] = None
    installment_number: Optional[int] = Field(None, ge=1)
    total_installments: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None

    # Validação repetida aqui pois os campos são opcionais no Update
    @validator('installment_number')
    def validate_installment_update(cls, v, values):
        total = values.get('total_installments')
        # Nota: Validação completa em updates parciais é complexa, 
        # mas garantimos que se ambos forem enviados, a lógica se mantém.
        if total and v and v > total:
            raise ValueError('Parcela atual não pode ser maior que o total')
        return v

# ==========================================
# 4. RESPONSE: O que o Backend devolve
# ==========================================
class TransactionResponse(TransactionBase):
    """
    Schema completo retornado para o Frontend.
    Inclui IDs e campos calculados pelo banco.
    """
    id: int
    user_id: int
    
    # O status agora é retornado explicitamente (PAID/PENDING/CANCELLED)
    # vindo da coluna real do banco de dados.
    status: TransactionStatus 
    
    created_at: datetime
    updated_at: datetime

    class Config:
        # Permite converter o objeto SQLAlchemy direto para Pydantic
        from_attributes = True 

# ==========================================
# 5. FILTER: Para o Dashboard e Extrato
# ==========================================
class TransactionFilter(BaseModel):
    """
    Schema avançado para filtrar dados no Service.
    Usado para gerar relatórios e alimentar o grid.
    """
    user_id: int
    
    # --- Filtros de Período (Obrigatórios para performance) ---
    month: Optional[int] = Field(None, ge=1, le=12, description="Mês de competência")
    year: Optional[int] = Field(None, ge=2000, description="Ano de competência")
    
    start_date: Optional[date] = Field(None, description="Início do range personalizado")
    end_date: Optional[date] = Field(None, description="Fim do range personalizado")
    
    # --- Filtros de Atributos ---
    description: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    status: Optional[TransactionStatus] = None # Filtrar só PENDENTE ou PAGO
    
    # --- Ordenação e Paginação ---
    sort_by: Optional[str] = Field("date", description="Campo para ordenação")
    sort_desc: bool = True
    limit: int = 100
    offset: int = 0