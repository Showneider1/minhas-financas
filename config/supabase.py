"""
Integração opcional com Supabase.

Escopo desta fase: PREPARAÇÃO LOCAL, sem credenciais reais.
- Não substitui o SQLAlchemy (dono transacional do schema).
- Cliente `supabase-py` é lazy e opcional: só é criado se
  SUPABASE_URL + (ANON_KEY ou SERVICE_ROLE) estiverem configurados
  E o pacote `supabase` estiver instalado.
- NUNCA exponha SERVICE_ROLE no frontend. Este módulo é backend-only.
- Sem credenciais → funções retornam None e logam aviso, sem quebrar o app.

Uso futuro (quando houver projeto Supabase):
    from config.supabase import get_supabase_client, is_supabase_configured
"""
import logging
import os

logger = logging.getLogger("config.supabase")


def is_supabase_configured() -> bool:
    """Retorna True apenas se URL + alguma chave existirem (nomes, sem valores logados)."""
    url = os.getenv("SUPABASE_URL", "").strip()
    anon = os.getenv("SUPABASE_ANON_KEY", "").strip()
    service = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    return bool(url and (anon or service))


def get_supabase_client(use_service_role: bool = False):
    """
    Cria (lazy) o cliente Supabase ou retorna None se não configurado.

    Args:
        use_service_role: use APENAS no backend para tarefas admin
            (nunca no frontend, nunca expor ao browser).
    """
    url = os.getenv("SUPABASE_URL", "").strip()
    anon = os.getenv("SUPABASE_ANON_KEY", "").strip()
    service = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    key = service if use_service_role else anon
    if use_service_role and not service:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY ausente — cliente service_role não criado.")
        return None
    if not url or not key:
        logger.info("Supabase não configurado (SUPABASE_URL/KEY ausentes) — integração desativada.")
        return None

    try:
        from supabase import create_client  # dependencia opcional
    except ImportError:
        logger.warning("Pacote 'supabase' não instalado — execute: pip install supabase")
        return None

    if use_service_role:
        logger.warning("Cliente Supabase service_role criado — uso restrito ao backend.")
    return create_client(url, key)


def get_pooler_url() -> str:
    """Retorna a URL do pooler (sem logar valor — chamador não deve logar)."""
    return os.getenv("SUPABASE_DB_URL_POOLER", "").strip()
