"""
Repository para operações com usuários.
"""
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database.models.user import User


class UserRepository:
    """Repository de usuários com métodos específicos."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Busca usuário ativo por email.

        ──────────────────────────────────────────────────────────────
        BUG 7 CORRIGIDO: o filtro `User.is_deleted == False` já estava
        presente neste método — verificado no código original.
        Adicionamos também o filtro em get_by_id, que estava ausente,
        garantindo que usuários com soft delete não sejam retornados
        em nenhum ponto do sistema.
        ──────────────────────────────────────────────────────────────
        """
        return (
            self.db.query(User)
            .filter(User.email == email, User.is_deleted == False)
            .first()
        )

    def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        """Verifica se email já está cadastrado (ignora usuários deletados)."""
        query = self.db.query(User.id).filter(
            User.email == email,
            User.is_deleted == False,
        )
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        return query.first() is not None

    def create_user(self, name: str, email: str, password_hash: str) -> User:
        """Cria novo usuário."""
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Busca usuário por ID.
        BUG 7 CORRIGIDO: filtro is_deleted adicionado — antes retornava
        usuários deletados via soft delete, expondo dados indevidos.
        """
        return (
            self.db.query(User)
            .filter(User.id == user_id, User.is_deleted == False)
            .first()
        )

    def soft_delete_user(self, user_id: int) -> bool:
        """
        Marca usuário como deletado (soft delete) sem remover do banco.
        Desativa o usuário simultaneamente para bloquear novos logins.
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_deleted = True
            user.is_active  = False
            self.db.flush()
            return True
        return False

    def update_last_login(self, user_id: int):
        """
        Atualiza timestamp do último login.
        BUG 8 CORRIGIDO: usa datetime.now(timezone.utc) em vez de utcnow().
        """
        user = self.get_by_id(user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            self.db.flush()

    def activate_user(self, user_id: int) -> bool:
        """Ativa usuário."""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            self.db.flush()
            return True
        return False

    def deactivate_user(self, user_id: int) -> bool:
        """Desativa usuário sem deletar."""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.db.flush()
            return True
        return False
