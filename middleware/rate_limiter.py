"""
Sistema de rate limiting para proteção contra ataques.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple
from config.settings import settings


class RateLimiter:
    """
    Rate limiter simples baseado em memória.
    """

    def __init__(self):
        self._login_attempts: Dict[str, list] = {}

    def check_login_attempts(self, email: str) -> Tuple[bool, int]:
        """
        Verifica se email excedeu limite de tentativas.

        Returns:
            Tupla (permitido: bool, retry_after: int)
        """
        if email not in self._login_attempts:
            return True, 0

        # Remove tentativas antigas
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.RATE_LIMIT_WINDOW_SECONDS)
        self._login_attempts[email] = [
            attempt for attempt in self._login_attempts[email]
            if attempt > cutoff
        ]

        # Verifica limite
        count = len(self._login_attempts[email])
        if count >= settings.RATE_LIMIT_LOGIN_ATTEMPTS:
            oldest = min(self._login_attempts[email])
            retry_after = int(
                (oldest + timedelta(seconds=settings.RATE_LIMIT_WINDOW_SECONDS) - datetime.now(timezone.utc)).total_seconds()
            )
            return False, max(0, retry_after)

        return True, 0

    def record_login_attempt(self, email: str):
        """Registra tentativa de login."""
        if email not in self._login_attempts:
            self._login_attempts[email] = []
        self._login_attempts[email].append(datetime.now(timezone.utc))

    def clear_login_attempts(self, email: str):
        """Limpa tentativas de login após sucesso."""
        if email in self._login_attempts:
            del self._login_attempts[email]


# Instância global
rate_limiter = RateLimiter()