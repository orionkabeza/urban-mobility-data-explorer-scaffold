"""In-memory transaction store shared by the API layer and the DSA benchmark.

Turns the flat list dsa/parse_sms.py produces into two shapes: a list for
linear scans, and an id -> record dict for O(1) lookups and the API's CRUD
handlers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dsa.parse_sms import DEFAULT_JSON_PATH, DEFAULT_XML_PATH, parse_file, to_json
import json


class TransactionStore:
    def __init__(self, transactions: list[dict[str, Any]]):
        self._by_id: dict[int, dict[str, Any]] = {t["id"]: t for t in transactions}
        self._next_id = max(self._by_id, default=0) + 1

    def list(self) -> list[dict[str, Any]]:
        return list(self._by_id.values())

    def as_dict(self) -> dict[int, dict[str, Any]]:
        return self._by_id

    def get(self, transaction_id: int) -> dict[str, Any] | None:
        return self._by_id.get(transaction_id)

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        record = {**fields, "id": self._next_id}
        self._by_id[self._next_id] = record
        self._next_id += 1
        return record

    def update(self, transaction_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
        record = self._by_id.get(transaction_id)
        if record is None:
            return None
        record.update({k: v for k, v in fields.items() if k != "id"})
        return record

    def delete(self, transaction_id: int) -> bool:
        return self._by_id.pop(transaction_id, None) is not None


def load_store(json_path: Path | str = DEFAULT_JSON_PATH, xml_path: Path | str = DEFAULT_XML_PATH) -> TransactionStore:
    """Loads from the pre-parsed JSON if present, else parses the XML fresh."""
    json_path = Path(json_path)
    if json_path.exists():
        transactions = json.loads(json_path.read_text(encoding="utf-8"))
    else:
        result = parse_file(xml_path)
        to_json(result, json_path)
        transactions = result["transactions"]
    return TransactionStore(transactions)
