"""Serviço de Importação e Conciliação Bancária (OFX/CSV).

Responsável por:
- Ler arquivos OFX e CSV
- Normalizar datas, valores e descrições
- Gerar uma chave de conciliação (`external_id`) por transação
- Sugerir se a linha é nova (`READY_TO_IMPORT`) ou duplicada (`DUPLICATE_FOUND`)
- Importar em lote com categorias escolhidas pelo usuário

Regras:
- Valores são sempre `Decimal`
- `TRANSFER` nunca é criado por importação
- Duplicatas são detectadas por `external_id` ou `import_hash`
"""

from __future__ import annotations

import hashlib
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from typing import Any

import pandas as pd
from ofxparse import OfxParser
from sqlalchemy.orm import Session

from config.logging_config import app_logger
from database.enums import TransactionType
from database.models.account import Account
from database.models.category import Category
from database.models.transaction import Transaction
from services.import_categorizer import auto_categorize

READY_TO_IMPORT = "READY_TO_IMPORT"
DUPLICATE_FOUND = "DUPLICATE_FOUND"

BANK_SCHEMAS = {
    "nubank": {"data": "date", "valor": "amount", "descricao": "title"},
    "bradesco": {"data": "Data", "valor": "Valor", "descricao": "Histórico"},
    "itau": {"data": "Data", "valor": "Valor", "descricao": "Lançamento"},
    "inter": {"data": "Data lançamento", "valor": "Valor", "descricao": "Descrição"},
    "santander": {"data": "Data", "valor": "Valor", "descricao": "Descrição"},
    "c6": {"data": "Data", "valor": "Valor", "descricao": "Descrição"},
}

_DATE_CANDIDATES = [
    "date",
    "data",
    "data lançamento",
    "dt",
    "data_lancamento",
    "data lancamento",
]
_AMOUNT_CANDIDATES = ["amount", "valor", "value", "quantia", "montante"]
_DESC_CANDIDATES = [
    "title",
    "description",
    "descricao",
    "descrição",
    "histórico",
    "historico",
    "lançamento",
    "lancamento",
    "memo",
    "detalhe",
    "detalhes",
]


class ImportService:
    """Importação de extratos bancários com conciliação idempotente."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def parse_file(
        self,
        file_content: bytes,
        *,
        filename: str,
        account_id: int,
        user_id: int,
    ) -> list[dict[str, Any]]:
        """Lê um arquivo OFX ou CSV e devolve linhas normalizadas."""
        self._validate_account(account_id, user_id)

        suffix = PurePosixPath(filename.lower()).suffix
        if suffix == ".ofx":
            rows = self._parse_ofx(file_content)
        elif suffix == ".csv":
            rows = self._parse_csv(file_content)
        else:
            raise ValueError("Formato não suportado. Use .ofx ou .csv")

        normalized: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            normalized.append(
                self._normalize_row(
                    row,
                    index=index,
                    account_id=account_id,
                    user_id=user_id,
                )
            )

        return self._annotate_duplicates(normalized, user_id=user_id)

    def process_import(
        self,
        rows: list[dict[str, Any]],
        *,
        category_ids: list[int | None],
        account_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """Importa apenas as linhas prontas, respeitando a categoria escolhida."""
        from schemas.transaction_schema import TransactionCreate
        from services.finance_service import FinanceService

        self._validate_account(account_id, user_id)

        results: dict[str, Any] = {
            "imported": 0,
            "skipped": 0,
            "errors": [],
        }

        if not rows:
            return results

        external_ids = [row.get("external_id") for row in rows if row.get("external_id")]
        import_hashes = [row.get("import_hash") for row in rows if row.get("import_hash")]
        existing = self._find_existing_keys(
            user_id=user_id,
            external_ids=external_ids,
            import_hashes=import_hashes,
        )

        for index, row in enumerate(rows):
            try:
                if row.get("status") == DUPLICATE_FOUND:
                    results["skipped"] += 1
                    continue

                if row.get("external_id") in existing["external_ids"]:
                    results["skipped"] += 1
                    continue

                if row.get("import_hash") in existing["import_hashes"]:
                    results["skipped"] += 1
                    continue

                category_id = self._resolve_category(
                    row=row,
                    category_id=category_ids[index] if index < len(category_ids) else None,
                    user_id=user_id,
                )

                transaction_date = self._parse_date_value(row["date"])
                amount = self._parse_amount_value(row["amount"])
                transaction_type = TransactionType(row["transaction_type"])

                payload = TransactionCreate(
                    description=row["description"],
                    base_amount=abs(amount),
                    transaction_type=transaction_type,
                    category_id=category_id,
                    account_id=account_id,
                    purchase_date=transaction_date,
                    due_date=transaction_date,
                    paid_date=None,
                    notes=f"import_hash:{row['import_hash']} fonte:import",
                )

                transaction = FinanceService(self.db).create_transaction(user_id, payload)
                transaction.import_hash = row["import_hash"]
                transaction.external_id = row["external_id"]
                transaction.categorization_source = "import"
                self.db.flush()
                self.db.commit()

                results["imported"] += 1
                existing["external_ids"].add(row["external_id"])
                existing["import_hashes"].add(row["import_hash"])

            except Exception as exc:
                self.db.rollback()
                results["errors"].append(
                    {
                        "line": index + 1,
                        "error": str(exc),
                    }
                )
                app_logger.warning(f"[ImportService] Erro na linha {index + 1}: {exc}")

        app_logger.info(
            f"[ImportService] Importação concluída: "
            f"{results['imported']} importadas, "
            f"{results['skipped']} duplicadas, "
            f"{len(results['errors'])} erros"
        )
        return results

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------
    def _parse_ofx(self, content: bytes) -> list[dict[str, Any]]:
        try:
            ofx = OfxParser.parse(io.BytesIO(content))
            transactions = ofx.account.statement.transactions
        except Exception as exc:
            raise ValueError(f"Não foi possível ler o arquivo OFX: {exc}") from exc

        rows: list[dict[str, Any]] = []
        for transaction in transactions:
            amount = self._to_decimal(transaction.amount)
            posted_date = (
                transaction.date.date()
                if isinstance(transaction.date, datetime)
                else transaction.date
            )
            description = (transaction.payee or transaction.memo or "").strip()
            if not description:
                description = (transaction.memo or "Transação importada").strip()

            rows.append(
                {
                    "date": posted_date,
                    "amount": amount,
                    "description": description,
                    "fitid": (transaction.id or "").strip(),
                }
            )

        if not rows:
            raise ValueError("O arquivo OFX não contém transações.")
        return rows

    def _parse_csv(self, content: bytes) -> list[dict[str, Any]]:
        try:
            dataframe = pd.read_csv(
                io.BytesIO(content),
                sep=None,
                engine="python",
                dtype=str,
            )
            dataframe.columns = dataframe.columns.str.strip()
        except Exception as exc:
            raise ValueError(f"Não foi possível ler o arquivo CSV: {exc}") from exc

        col_map = _detect_column_schema(dataframe)
        dataframe = dataframe.rename(columns=col_map)

        rows: list[dict[str, Any]] = []
        for index, row in dataframe.iterrows():
            try:
                amount = _parse_valor(row["valor"])
                transaction_date = _parse_date(row["data"])
                description = str(
                    row.get("descricao", f"Transação importada linha {index + 1}")
                ).strip()

                rows.append(
                    {
                        "date": transaction_date,
                        "amount": amount,
                        "description": description,
                        "fitid": "",
                    }
                )
            except Exception as exc:
                raise ValueError(f"Erro na linha {index + 1}: {exc}") from exc

        if not rows:
            raise ValueError("O arquivo CSV não contém transações.")
        return rows

    # ------------------------------------------------------------------
    # Normalização e dedupe
    # ------------------------------------------------------------------
    def _normalize_row(
        self,
        row: dict[str, Any],
        *,
        index: int,
        account_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        amount = self._to_decimal(row["amount"])
        if amount == 0:
            raise ValueError(f"Valor inválido na linha {index + 1}")

        transaction_date = self._parse_date_value(row["date"])
        description = (row.get("description") or "Transação importada").strip()
        transaction_type = TransactionType.INCOME if amount > 0 else TransactionType.EXPENSE

        fitid = (row.get("fitid") or "").strip()
        reconciliation_hash = self._make_hash(
            transaction_date=transaction_date,
            amount=abs(amount),
            description=description,
            user_id=user_id,
            account_id=account_id,
        )

        if fitid:
            external_id = f"ofx:{account_id}:{fitid}"
        else:
            external_id = f"hash:{reconciliation_hash}"

        suggested_category_id = auto_categorize(description, user_id, self.db)
        if suggested_category_id is None:
            suggested_category_id = self._fallback_category_id(
                user_id=user_id,
                transaction_type=transaction_type,
            )

        return {
            "index": index,
            "date": transaction_date.isoformat(),
            "description": description,
            "amount": str(abs(amount)),
            "transaction_type": transaction_type.value,
            "external_id": external_id,
            "import_hash": reconciliation_hash,
            "suggested_category_id": suggested_category_id,
            "status": READY_TO_IMPORT,
        }

    def _annotate_duplicates(
        self,
        rows: list[dict[str, Any]],
        *,
        user_id: int,
    ) -> list[dict[str, Any]]:
        external_ids = [row["external_id"] for row in rows]
        import_hashes = [row["import_hash"] for row in rows]
        existing = self._find_existing_keys(
            user_id=user_id,
            external_ids=external_ids,
            import_hashes=import_hashes,
        )

        for row in rows:
            if (
                row["external_id"] in existing["external_ids"]
                or row["import_hash"] in existing["import_hashes"]
            ):
                row["status"] = DUPLICATE_FOUND
            else:
                row["status"] = READY_TO_IMPORT

        return rows

    def _find_existing_keys(
        self,
        *,
        user_id: int,
        external_ids: list[str],
        import_hashes: list[str],
    ) -> dict[str, set[str]]:
        existing_external_ids: set[str] = set()
        existing_import_hashes: set[str] = set()

        if external_ids:
            query = self.db.query(Transaction.external_id).filter(
                Transaction.user_id == user_id,
                Transaction.external_id.in_(external_ids),
            )
            existing_external_ids = {row[0] for row in query.all() if row[0]}

        if import_hashes:
            query = self.db.query(Transaction.import_hash).filter(
                Transaction.user_id == user_id,
                Transaction.import_hash.in_(import_hashes),
            )
            existing_import_hashes = {row[0] for row in query.all() if row[0]}

        return {
            "external_ids": existing_external_ids,
            "import_hashes": existing_import_hashes,
        }

    # ------------------------------------------------------------------
    # Validações e helpers
    # ------------------------------------------------------------------
    def _validate_account(self, account_id: int, user_id: int) -> None:
        account = (
            self.db.query(Account)
            .filter(
                Account.id == account_id,
                Account.user_id == user_id,
                Account.is_deleted.is_(False),
            )
            .first()
        )
        if not account:
            raise ValueError("Conta não encontrada para este usuário.")
        if not account.is_active:
            raise ValueError("Conta está inativa.")

    def _resolve_category(
        self,
        *,
        row: dict[str, Any],
        category_id: int | None,
        user_id: int,
    ) -> int:
        if category_id is None:
            category_id = row.get("suggested_category_id")

        if category_id is None:
            category_id = self._fallback_category_id(
                user_id=user_id,
                transaction_type=TransactionType(row["transaction_type"]),
            )

        category = (
            self.db.query(Category)
            .filter(
                Category.id == category_id,
                (Category.user_id == user_id) | (Category.is_system.is_(True)),
            )
            .first()
        )
        if not category:
            raise ValueError("Categoria inválida para este usuário.")

        expected_type = TransactionType(row["transaction_type"])
        if category.transaction_type is not None and category.transaction_type != expected_type:
            raise ValueError("Categoria incompatível com o tipo da transação.")

        return category.id

    def _fallback_category_id(
        self,
        *,
        user_id: int,
        transaction_type: TransactionType,
    ) -> int:
        category = (
            self.db.query(Category)
            .filter(
                Category.transaction_type == transaction_type,
                (Category.user_id == user_id) | (Category.is_system.is_(True)),
            )
            .order_by(Category.user_id.desc())
            .first()
        )
        if category:
            return category.id

        label = "receitas" if transaction_type == TransactionType.INCOME else "despesas"
        category = Category(
            user_id=user_id,
            name=f"Importados ({label})",
            transaction_type=transaction_type,
            icon="📥",
            color="#95a5a6",
            is_system=False,
        )
        self.db.add(category)
        self.db.flush()
        return category.id

    @staticmethod
    def _make_hash(
        *,
        transaction_date: date,
        amount: Decimal,
        description: str,
        user_id: int,
        account_id: int,
    ) -> str:
        key = (
            f"{user_id}|{account_id}|{transaction_date.isoformat()}|"
            f"{amount:.2f}|{description.upper().strip()}"
        )
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Valor monetário inválido: '{value}'") from exc

    @staticmethod
    def _parse_date_value(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return _parse_date(value)

    @staticmethod
    def _parse_amount_value(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Valor monetário inválido: '{value}'") from exc


# ------------------------------------------------------------------ #
# Helpers compatíveis com a API antiga                                 #
# ------------------------------------------------------------------ #


def _detect_column_schema(df: pd.DataFrame) -> dict:
    cols_lower = {c.lower().strip(): c for c in df.columns}

    for bank, schema in BANK_SCHEMAS.items():
        match_data = schema["data"].lower() in cols_lower
        match_valor = schema["valor"].lower() in cols_lower
        match_desc = schema["descricao"].lower() in cols_lower
        if match_data and match_valor and match_desc:
            app_logger.debug(f"[ImportService] Schema detectado: {bank}")
            return {
                cols_lower[schema["data"].lower()]: "data",
                cols_lower[schema["valor"].lower()]: "valor",
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
            f"Não foi possível detectar as colunas: {missing}. "
            f"Colunas encontradas no CSV: {list(df.columns)}"
        )
    return col_map


def _parse_valor(raw: str) -> Decimal:
    clean = re.sub(r"[^\d,.\-]", "", str(raw)).strip()
    if re.search(r"\d\.\d{3},\d{2}$", clean):
        clean = clean.replace(".", "").replace(",", ".")
    else:
        clean = clean.replace(",", ".")

    try:
        return Decimal(clean)
    except InvalidOperation as exc:
        raise ValueError(f"Valor monetário inválido: '{raw}'") from exc


def _parse_date(raw: str) -> date:
    raw = str(raw).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato de data não reconhecido: '{raw}'")


def import_from_csv(
    file_content: bytes,
    account_id: int,
    user_id: int,
    db: Session,
) -> dict:
    """Compatibilidade com a API antiga de importação CSV."""
    service = ImportService(db)
    rows = service.parse_file(
        file_content,
        filename="extrato.csv",
        account_id=account_id,
        user_id=user_id,
    )

    category_ids = [row.get("suggested_category_id") for row in rows]
    return service.process_import(
        rows,
        category_ids=category_ids,
        account_id=account_id,
        user_id=user_id,
    )
