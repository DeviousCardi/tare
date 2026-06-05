"""The registry, which reads and never writes."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass

from tare.common.errors import not_found
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator
from tare.modules.registry.rules import SHELVES, describes, knows, shelf_names


class RegistryService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def _table(self, name: str):
        if not knows(name):
            raise not_found("shelf", name)
        return getattr(self.store, SHELVES[name][0])

    def shelves(self, operator: Operator) -> list[dict]:
        """Every shelf the registry holds, and how much is on it."""
        return [{"name": name, "describes": describes(name),
                 "rows": len(self._table(name))}
                for name in shelf_names()]

    def rows(self, operator: Operator, name: str, limit: int | None = None,
             offset: int | None = None) -> dict:
        table = self._table(name)
        answer = page(table.all(), limit, offset)
        return {"name": name,
                "data": [asdict(row) if is_dataclass(row) else dict(row)
                         for row in answer["data"]],
                "total": answer["total"]}

    def count(self, operator: Operator, name: str) -> int:
        return len(self._table(name))
