"""Entitlements, and what is left of one."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Entitlement, Operator
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.entitlements.rules import (
    carry_forward, earned_by, for_year, remaining, sort_by_year, total_available,
    year_ends_on,
)
from tare.modules.entitlements.schemas import (
    ChangeEntitlement, GrantEntitlement, ListEntitlements,
)
from tare.modules.leave.service import LeaveService


class EntitlementsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.leave = LeaveService(store)

    def list(self, operator: Operator, query: ListEntitlements) -> dict:
        rows = visible_to(operator, self.store.entitlements.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.year_starts_on:
            starts = a_day(query.year_starts_on, "year_starts_on")
            rows = [row for row in rows if row.year_starts_on == starts]
        return page(sort_by_year(rows), query.limit, query.offset)

    def get(self, operator: Operator, entitlement_id: str) -> Entitlement:
        row = self.store.entitlements.find(entitlement_id)
        if not row:
            raise not_found("entitlement", entitlement_id)
        self.employees.get(operator, row.employee_id)
        return row

    def covering(self, operator: Operator, employee_id: str, day: str) -> Entitlement:
        self.employees.get(operator, employee_id)
        found = for_year(self.store.entitlements.all(), employee_id, a_day(day, "day"))
        if not found:
            raise not_found("entitlement covering", f"{employee_id} on {day}")
        return found

    def grant(self, operator: Operator, dto: GrantEntitlement) -> Entitlement:
        person = self.employees.get(operator, dto.employee_id)
        starts = a_day(dto.year_starts_on, "year_starts_on")
        clash = self.store.entitlements.first(
            lambda row: row.employee_id == person.id and row.year_starts_on == starts)
        if clash:
            raise conflict(f"{person.reference} already has a year from {starts}")
        return self.store.entitlements.insert(Entitlement(
            id="", employee_id=person.id, employer_id=person.employer_id,
            year_starts_on=starts, days=dto.days, carried_in=dto.carried_in))

    def change(
        self, operator: Operator, entitlement_id: str, dto: ChangeEntitlement,
    ) -> Entitlement:
        row = self.get(operator, entitlement_id)
        changes = {name: value for name, value in dto.model_dump().items()
                   if value is not None}
        if not changes:
            raise refuse("nothing was asked to change")
        return self.store.entitlements.update(row.id, **changes)

    def balance(self, operator: Operator, employee_id: str, day: str) -> dict:
        person = self.employees.get(operator, employee_id)
        row = self.covering(operator, employee_id, day)
        ends = year_ends_on(row)
        taken = self.leave.taken(operator, employee_id, row.year_starts_on, ends)["days"]
        return {
            "employee_id": employee_id,
            "year_starts_on": row.year_starts_on,
            "year_ends_on": ends,
            "earned": earned_by(row, person.joined_on, person.left_on),
            "carried_in": row.carried_in,
            "available": total_available(row, person.joined_on, person.left_on),
            "taken": taken,
            "remaining": remaining(row, person.joined_on, person.left_on, taken),
            "carry_forward": carry_forward(row, person.joined_on, person.left_on, taken),
        }
