"""
Servico de Pre-Categorizacao Inteligente com Fuzzy Matching.

Ao importar transacoes bancarias, este modulo tenta inferir
automaticamente a category_id comparando a descricao do lancamento
com o historico de transacoes ja categorizadas pelo usuario.

Dependencias:
    pip install rapidfuzz
"""
import re
from typing import Optional

from rapidfuzz import process, fuzz
from sqlalchemy.orm import Session

from config.logging_config import app_logger


def normalize_description(text: str) -> str:
    """
    Normaliza descricao para comparacao fuzzy.

    Exemplos:
        'UBER *TRIP 1234'  -> 'UBER TRIP'
        'PAGTO CELULAR 05' -> 'PAGTO CELULAR'
    """
    text = text.upper().strip()
    text = re.sub(r"\*", " ", text)
    text = re.sub(r"\d{4,}", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def auto_categorize(
    description: str,
    user_id: int,
    db: Session,
    threshold: int = 75,
) -> Optional[int]:
    """
    Infere category_id pelo historico de transacoes do usuario.

    Niveis de confianca:
        >= 90: Categoriza automaticamente
        75-89: Retorna sugestao (chamador decide se aplica)
        < 75:  Retorna None (usuario categoriza manualmente)
    """
    result = db.execute(
        """
        SELECT t.description, t.category_id, COUNT(*) as freq
        FROM transactions t
        WHERE t.user_id = :user_id
          AND t.category_id IS NOT NULL
        GROUP BY UPPER(TRIM(t.description)), t.category_id
        ORDER BY freq DESC
        """,
        {"user_id": user_id},
    ).fetchall()

    if not result:
        return None

    history      = [{"description": row[0], "category_id": row[1]} for row in result]
    descriptions = [normalize_description(row["description"]) for row in history]
    desc_clean   = normalize_description(description)

    match = process.extractOne(
        desc_clean,
        descriptions,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
    )

    if match:
        matched_desc, score, idx = match
        category_id = history[idx]["category_id"]
        app_logger.debug(
            f"[Categorizer] Match: '{desc_clean}' -> '{matched_desc}' "
            f"(score={score}, category_id={category_id})"
        )
        return category_id

    app_logger.debug(f"[Categorizer] Sem match acima de {threshold} para: '{desc_clean}'")
    return None


def get_categorization_confidence(score: int) -> str:
    """Retorna nivel de confianca para exibicao na UI."""
    if score >= 90:
        return "auto"
    elif score >= 75:
        return "suggested"
    return "manual"
