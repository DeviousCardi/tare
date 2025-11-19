"""Exemptions, and who may grant one."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Exemption, Operator
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.exemptions.rules import (
    KINDS, covers, kinds_standing, sort_by_start, standing_for,
)
from tare.modules.exemptions.schemas import EndExemption, GrantExemption, ListExemptions


class ExemptionsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def _mine(self, operator: Operator) -> list[Exemption]:
        """Exemptions belong to a person, so visibility follows the person."""
        from tare.modules.employees.schemas import ListEmployees

        seen = {row.id for row in
                self.employees.list(operator, ListEmployees(limit=500))["data"]}
        return [row for row in self.store.exemptions.all() if row.employee_id in seen]

    def list(self, operator: Operator, query: ListExemptions) -> dict:
        rows = self._mine(operator)
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.kind:
            rows = [row for row in rows if row.kind == query.kind]
        if query.standing_on:
            day = a_day(query.standing_on, "standing_on")
            rows = [row for row in rows if covers(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, exemption_id: str) -> Exemption:
        row = self.store.exemptions.find(exemption_id)
        if not row:
            raise not_found("exemption", exemption_id)
        self.employees.get(operator, row.employee_id)
        return row

    def grant(self, operator: Operator, dto: GrantExemption) -> Exemption:
        person = self.employees.get(operator, dto.employee_id)
        if dto.kind not in KINDS:
            raise refuse(f"{dto.kind} is not something anybody can be exempt from")
        starts_on = a_day(dto.starts_on, "starts_on")
        ends_on = a_day(dto.ends_on, "ends_on") if dto.ends_on else None
        if ends_on and compare_dates(ends_on, starts_on) < 0:
            raise refuse("an exemption cannot end before it starts")
        standing = standing_for(self.store.exemptions.all(), person.id, dto.kind, starts_on)
        if standing:
            raise conflict(
                f"{person.reference} is already exempt from {dto.kind} on {starts_on}")
        return self.store.exemptions.insert(Exemption(
            id="", employee_id=person.id, kind=dto.kind, reason=dto.reason,
            starts_on=starts_on, ends_on=ends_on))

    def end(self, operator: Operator, exemption_id: str, dto: EndExemption) -> Exemption:
        row = self.get(operator, exemption_id)
        ends_on = a_day(dto.ends_on, "ends_on")
        if row.ends_on is not None:
            raise conflict("that exemption has already ended")
        if compare_dates(ends_on, row.starts_on) < 0:
            raise refuse("an exemption cannot end before it starts")
        return self.store.exemptions.update(row.id, ends_on=ends_on)

    def standing(self, operator: Operator, employee_id: str, day: str) -> list[str]:
        self.employees.get(operator, employee_id)
        return kinds_standing(self.store.exemptions.all(), employee_id, a_day(day, "day"))
