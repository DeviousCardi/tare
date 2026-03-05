"""Protected earnings, and how much of a figure an order may reach."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, ProtectedEarnings
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.protections.rules import (
    available_for_orders, breaches, most_takeable, sort_by_start, standing_for,
    stands_on,
)
from tare.modules.protections.schemas import (
    EndProtection, ListProtections, SetProtection,
)


class ProtectionsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListProtections) -> dict:
        rows = visible_to(operator, self.store.protections.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.standing_on:
            day = a_day(query.standing_on, "standing_on")
            rows = [row for row in rows if stands_on(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, protection_id: str) -> ProtectedEarnings:
        row = self.store.protections.find(protection_id)
        if not row:
            raise not_found("protection", protection_id)
        self.employees.get(operator, row.employee_id)
        return row

    def standing(self, operator: Operator, employee_id: str, day: str) -> ProtectedEarnings:
        self.employees.get(operator, employee_id)
        found = standing_for(self.store.protections.all(), employee_id, a_day(day, "day"))
        if not found:
            raise not_found("protection standing", f"{employee_id} on {day}")
        return found

    def set(self, operator: Operator, dto: SetProtection) -> ProtectedEarnings:
        person = self.employees.get(operator, dto.employee_id)
        starts_on = a_day(dto.starts_on, "starts_on")
        ends_on = a_day(dto.ends_on, "ends_on") if dto.ends_on else None
        if ends_on and compare_dates(ends_on, starts_on) < 0:
            raise refuse("a protected floor cannot end before it starts")
        clash = standing_for(self.store.protections.all(), person.id, starts_on)
        if clash and clash.starts_on == starts_on:
            raise conflict(f"a floor already starts on {starts_on}")
        return self.store.protections.insert(ProtectedEarnings(
            id="", employee_id=person.id, employer_id=person.employer_id,
            floor=dto.floor, starts_on=starts_on, ends_on=ends_on))

    def end(
        self, operator: Operator, protection_id: str, dto: EndProtection,
    ) -> ProtectedEarnings:
        row = self.get(operator, protection_id)
        ends_on = a_day(dto.ends_on, "ends_on")
        if row.ends_on is not None:
            raise conflict("that floor has already ended")
        if compare_dates(ends_on, row.starts_on) < 0:
            raise refuse("a protected floor cannot end before it starts")
        return self.store.protections.update(row.id, ends_on=ends_on)

    def reach(self, operator: Operator, employee_id: str, day: str, pay: int,
              asked: int) -> dict:
        if pay < 0 or asked < 0:
            raise refuse("pay and what is asked for cannot be negative")
        row = self.standing(operator, employee_id, day)
        return {"employee_id": employee_id, "pay": pay, "floor": row.floor,
                "available": available_for_orders(pay, row.floor), "asked": asked,
                "takeable": most_takeable(pay, row.floor, asked),
                "breaches": breaches(pay, row.floor, asked)}
