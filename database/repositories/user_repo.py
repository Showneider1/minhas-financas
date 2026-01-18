"""
Repository para operações com usuários.
"""
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from database.models.user import User


class UserRepository:
    """
    Repository de usuários com métodos específicos.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Busca usuário por email.
        """
        return self.db.query(User).filter(
            User.email == email,
            User.is_deleted == False
        ).first()
    
    def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        """
        Verifica se email já está cadastrado.
        """
        query = self.db.query(User.id).filter(
            User.email == email,
            User.is_deleted == False
        )
        
        if exclude_id:
            query = query.filter(User.id != exclude_id)
        
        return query.first() is not None
    
    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
    ) -> User:
        """
        Cria novo usuário.
        """
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            is_active=True,
            is_verified=False,
        )
        
        self.db.add(user)
        self.db.flush()  # Faz flush para gerar o ID
        
        return user
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Busca usuário por ID.
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def update_last_login(self, user_id: int):
        """
        Atualiza timestamp do último login.
        """
        user = self.get_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            self.db.flush()
    
    def activate_user(self, user_id: int) -> bool:
        """
        Ativa usuário.
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            self.db.flush()
            return True
        return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        Desativa usuário.
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.db.flush()
            return True
        return False
