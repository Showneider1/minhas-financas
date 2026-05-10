"""
Servico de Importacao em Lote de Extratos Bancarios.

Responsavel por:
- Ler arquivos CSV exportados por bancos brasileiros (Nubank, Itau, Bradesco, Inter, etc.)
- Detectar automaticamente colunas (data, valor, descricao) via heuristica
- Classificar lancamentos como receita/despesa pelo sinal do valor
- Pre-categorizar usando fuzzy matching (import_categorizer)
- Deduplicar por hash para evitar double-entry

Uso:
    with get_db_session() as db:
        result = import_from_csv(file_bytes, account_id=1, user_id=1, db=db)
"""
import hashlib
import io
import re
from datetime import date, datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from database.connection import get_db_session
from services.import_categorizer import auto_categorize
from config.logging_config import app_logger


# ------------------------------------------------------------------ #
# MAPEAMENTO DE COLUNAS POR BANCO                                       #
# ------------------------------------------------------------------ #

BANK_SCHEMAS = {
    "nubank":    {"data": "date",            "valor": "amount", "descricao": "title"},
    "bradesco":  {"data": "Data",            "valor": "Valor",  "descricao": "Histórico"},
    "itau":      {"data": "Data",            "valor": "Valor",  "descricao": "Lançamento"},
    "inter":     {"data": "Data lançamento", "valor": "Valor",  "descricao": "Descrição"},
    "santander": {"data": "Data",            "valor": "Valor",  "descricao": "Descrição"},
    "c6":        {"data": "Data",            "valor": "Valor",  "descricao": "Descrição"},
}

_DATE_CANDIDATES   = ["date", "data", "data lançamento", "dt", "data_lancamento", "data lancamento"]
_AMOUNT_CANDIDATES = ["amount", "valor", "value", "quantia", "montante"]
_DESC_CANDIDATES   = [
    "title", "description", "descricao", "descrição",
    "histórico", "historico", "lançamento", "lancamento",
    "memo", "detalhe", "detalhes"
]


# ------------------------------------------------------------------ #
# HELPERS PRIVADOS                                                      #
# ------------------------------------------------------------------ #

def _detect_column_schema(df: pd.DataFrame) -> dict:
    cols_lower = {c.lower().strip(): c for c in df.columns}

    for bank, schema in BANK_SCHEMAS.items():
        match_data  = schema["data"].lower()      in cols_lower
        match_valor = schema["valor"].lower()     in cols_lower
        match_desc  = schema["descricao"].lower() in cols_lower
        if match_data and match_valor and match_desc:
            app_logger.debug(f"[ImportService] Schema detectado: {bank}")
            return {
                cols_lower[schema["data"].lower()]:      "data",
                cols_lower[schema["valor"].lower()]:     "valor",
                cols_lower[schema["descricao"].lower()]: "descricao",
            }

    col_map = {}
    for candidate in _DATE_CANDIDATES:
        if candidate in cols_lower:
            col_map[cols_lower[candidate]] = "data"
            break
    for candidate in _AMOUNT_CANDIDATES:
        if candidate in cols_lower:
            col_map[cols_lower[candidate]] = "valor"
            break
    for candidate in _DESC_CANDIDATES:
        if candidate in cols_lower:
            col_map[cols_lower[candidate]] = "descricao"
            break

    missing = {"data", "valor", "descricao"} - set(col_map.values())
    if missing:
        raise ValueError(
            f"Nao foi possivel detectar as colunas: {missing}. "
            f"Colunas encontradas no CSV: {list(df.columns)}"
        )
    return col_map


def _parse_valor(raw: str) -> float:
    clean = re.sub(r"[^\d,.\-]", "", str(raw)).strip()
    if re.search(r"\d\.\d{3},\d{2}$", clean):
        clean = clean.replace(".", "").replace(",", ".")
    else:
        clean = clean.replace(",", ".")
    return float(clean)


def _parse_date(raw: str) -> date:
    raw = str(raw).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato de data nao reconhecido: '{raw}'")


def _make_duplicate_hash(transaction_date: date, valor: float, descricao: str, user_id: int) -> str:
    key = f"{transaction_date.isoformat()}|{round(valor, 2)}|{descricao.upper().strip()}|{user_id}"
    return hashlib.sha256(key.encode()).hexdigest()


def _is_duplicate(db: Session, transaction_date: date, valor: float, descricao: str, user_id: int) -> bool:
    try:
        hash_key = _make_duplicate_hash(transaction_date, valor, descricao, user_id)
        result = db.execute(
            "SELECT 1 FROM transactions WHERE import_hash = :h AND user_id = :u LIMIT 1",
            {"h": hash_key, "u": user_id},
        ).fetchone()
        return result is not None
    except Exception:
        return False


def _insert_transaction(
    db: Session,
    row: pd.Series,
    tipo: str,
    valor: float,
    category_id: Optional[int],
    account_id: int,
    user_id: int,
    transaction_date: date,
) -> None:
    hash_key   = _make_duplicate_hash(transaction_date, valor, str(row.get("descricao", "")), user_id)
    cat_source = "auto" if category_id else "import"

    db.execute(
        """
        INSERT INTO transactions
            (user_id, account_id, category_id, description, amount,
             transaction_type, status, due_date, import_hash, categorization_source)
        VALUES
            (:user_id, :account_id, :category_id, :description, :amount,
             :transaction_type, 'PENDING', :due_date, :import_hash, :cat_source)
        """,
        {
            "user_id":          user_id,
            "account_id":       account_id,
            "category_id":      category_id,
            "description":      str(row.get("descricao", ""))[:255],
            "amount":           valor,
            "transaction_type": tipo.upper(),
            "due_date":         transaction_date.isoformat(),
            "import_hash":      hash_key,
            "cat_source":       cat_source,
        },
    )


# ------------------------------------------------------------------ #
# FUNCAO PRINCIPAL                                                      #
# ------------------------------------------------------------------ #

def import_from_csv(
    file_content: bytes,
    account_id: int,
    user_id: int,
    db: Session,
) -> dict:
    """
    Importa extrato bancario CSV e registra as transacoes no banco.

    Returns:
        {'imported': int, 'skipped': int, 'errors': list}
    """
    results = {"imported": 0, "skipped": 0, "errors": []}

    try:
        df = pd.read_csv(io.BytesIO(file_content), sep=None, engine="python", dtype=str)
        df.columns = df.columns.str.strip()
    except Exception as exc:
        raise ValueError(f"Nao foi possivel ler o arquivo CSV: {exc}") from exc

    col_map = _detect_column_schema(df)
    df = df.rename(columns=col_map)

    for idx, row in df.iterrows():
        try:
            valor            = _parse_valor(row["valor"])
            transaction_date = _parse_date(row["data"])
            descricao        = str(row.get("descricao", f"Importado linha {idx}")).strip()

            tipo  = "INCOME"  if valor > 0 else "EXPENSE"
            valor = abs(valor)

            if _is_duplicate(db, transaction_date, valor, descricao, user_id):
                results["skipped"] += 1
                continue

            category_id = auto_categorize(descricao, user_id, db)

            _insert_transaction(
                db=db, row=row, tipo=tipo, valor=valor,
                category_id=category_id, account_id=account_id,
                user_id=user_id, transaction_date=transaction_date,
            )
            results["imported"] += 1

        except Exception as row_exc:
            results["errors"].append({"linha": int(idx) + 1, "erro": str(row_exc)})
            app_logger.warning(f"[ImportService] Erro na linha {idx + 1}: {row_exc}")

    app_logger.info(
        f"[ImportService] Importacao concluida: "
        f"{results['imported']} importadas, "
        f"{results['skipped']} duplicatas, "
        f"{len(results['errors'])} erros"
    )
    return results
