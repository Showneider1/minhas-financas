"""Checker de conexão Supabase/Postgres (staging).

Uso:
    venv/Scripts/python.exe scripts/check_supabase_connection.py

Lê (sem exibir valores):
    SUPABASE_DB_URL_POOLER (preferido) ou DATABASE_URL_TARGET (fallback local)

Verifica: presença das vars, dialeto, TCP+login (SELECT 1, sem DDL),
versão do servidor e extensões úteis. Falha com mensagem acionável quando
as credenciais ainda não foram configuradas — nunca inventa valores.

Variáveis documentadas em .env.example.
"""

import os
import sys
from urllib.parse import urlsplit

REQUIRED_DOC = (
    "Configure no .env (veja .env.example): SUPABASE_DB_URL_POOLER "
    "(postgresql://...pooler.supabase.com:6543/postgres?sslmode=require). "
    "Sem credenciais, o staging remoto está bloqueado por design."
)


def _get_target_url() -> str:
    url = (
        os.getenv("SUPABASE_DB_URL_POOLER", "").strip()
        or os.getenv("MIGRATION_TARGET_URL", "").strip()
    )
    # Placeholders de preenchimento offline equivalem a ausente.
    if not url or "PREENCHER_OFFLINE" in url or "[USER]" in url:
        return ""
    return url


def _describe(url: str) -> str:
    try:
        parts = urlsplit(url)
    except Exception:
        return "URL inválida"
    host = parts.hostname or "(ausente)"
    if host not in ("localhost", "127.0.0.1"):
        host = "(remoto — oculto)"
    return f"dialeto={parts.scheme or '?'} host={host} porta={parts.port} db={parts.path}"


def main() -> int:
    # .env local é carregado pelo settings; aqui lemos env direto (sem logar valores).
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    url = _get_target_url()
    if not url:
        print("SUPABASE: credenciais ausentes.")
        print(REQUIRED_DOC)
        return 2

    print(f"SUPABASE: {_describe(url)}")
    scheme = urlsplit(url).scheme
    if scheme not in ("postgresql", "postgres"):
        print(f"SUPABASE: dialeto inesperado '{scheme}' (esperado postgresql).")
        return 2

    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        print(f"SUPABASE: SQLAlchemy indisponível: {exc}")
        return 2

    try:
        engine = create_engine(url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar() or "?"
            print(f"SUPABASE: conexão OK — {str(version).split(',')[0][:80]}")
            try:
                exts = conn.execute(text("SELECT extname FROM pg_extension ORDER BY 1")).fetchall()
                print(f"SUPABASE: extensões: {', '.join(e[0] for e in exts) or '(nenhuma)'}")
            except Exception:
                print("SUPABASE: sem permissão para listar extensões (ok para staging).")
        return 0
    except Exception as exc:
        print(f"SUPABASE: FALHA de conexão: {type(exc).__name__}")
        print("Verifique host/porta/senha, allowlist de IP e sslmode=require.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
