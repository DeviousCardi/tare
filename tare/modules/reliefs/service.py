"""Reliefs. Everybody reads them; only the bureau publishes one."""

from tare.common.effective import sort_by_effective
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Relief
from tare.modules.employers.schemas import a_day
from tare.modules.reliefs.rules import BASES, every_relief_on, for_code, relieved
from tare.modules.reliefs.schemas import ListReliefs, PublishRelief


class ReliefsService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def list(self, operator: Operator, query: ListReliefs) -> dict:
        rows = sort_by_effective(self.store.reliefs.all())
        if query.code:
            rows = [row for row in rows if row.code == query.code]
        if query.in_force_on:
            rows = every_relief_on(rows, a_day(query.in_force_on, "in_force_on"))
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, relief_id: str) -> Relief:
        row = self.store.reliefs.find(relief_id)
        if not row:
            raise not_found("relief", relief_id)
        return row

    def in_force(self, code: str, day: str) -> Relief:
        found = for_code(self.store.reliefs.all(), code, a_day(day, "day"))
        if not found:
            raise not_found("relief in force", f"{code} on {day}")
        return found

    def publish(self, operator: Operator, dto: PublishRelief) -> Relief:
        assert_bureau(operator, "publish a relief")
        effective_from = a_day(dto.effective_from, "effective_from")
        if dto.basis not in BASES:
            raise refuse(f"{dto.basis} is not a basis a relief is quoted on")
        if dto.basis == "share" and dto.amount > 10000:
            raise refuse("a share cannot be more than the whole")
        clash = self.store.reliefs.first(
            lambda row: row.code == dto.code and row.effective_from == effective_from)
        if clash:
            raise conflict(f"relief {dto.code} already changes on {effective_from}")
        return self.store.reliefs.insert(Relief(
            id="", code=dto.code, description=dto.description, basis=dto.basis,
            amount=dto.amount, effective_from=effective_from))

    def applied(self, code: str, day: str, pay: int) -> dict:
        return {"code": code, "pay": pay,
                "relieved": relieved(self.in_force(code, day), pay)}
