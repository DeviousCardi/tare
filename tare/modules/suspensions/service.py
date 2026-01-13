"""Suspensions, and which periods they hold a deduction off."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Suspension
from tare.modules.elements.service import ElementsService
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.suspensions.rules import (
    REASONS, covers, is_open, sort_by_period, suspended_elements,
)
from tare.modules.suspensions.schemas import (
    ListSuspensions, LiftSuspension, SuspendDeduction,
)


class SuspensionsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.elements = ElementsService(store)

    def list(self, operator: Operator, query: ListSuspensions) -> dict:
        rows = visible_to(operator, self.store.suspensions.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.element_id:
            rows = [row for row in rows if row.element_id == query.element_id]
        if query.open_only:
            rows = [row for row in rows if is_open(row)]
        return page(sort_by_period(rows), query.limit, query.offset)

    def get(self, operator: Operator, suspension_id: str) -> Suspension:
        row = self.store.suspensions.find(suspension_id)
        if not row:
            raise not_found("suspension", suspension_id)
        self.employees.get(operator, row.employee_id)
        return row

    def suspend(self, operator: Operator, dto: SuspendDeduction) -> Suspension:
        person = self.employees.get(operator, dto.employee_id)
        element = self.elements.get(operator, dto.element_id)
        if element.kind != "deduction":
            raise refuse("only a deduction can be suspended")
        if dto.reason not in REASONS:
            raise refuse(f"{dto.reason} is not a reason a deduction is suspended for")
        starts = a_day(dto.year_starts_on, "year_starts_on")
        standing = self.store.suspensions.first(
            lambda row: row.employee_id == person.id
            and row.element_id == dto.element_id
            and covers(row, dto.from_period, starts))
        if standing:
            raise conflict(
                f"{element.code} is already suspended for period {dto.from_period}")
        return self.store.suspensions.insert(Suspension(
            id="", employee_id=person.id, employer_id=person.employer_id,
            element_id=dto.element_id, reason=dto.reason,
            from_period=dto.from_period, to_period=None, year_starts_on=starts))

    def lift(self, operator: Operator, suspension_id: str, dto: LiftSuspension) -> Suspension:
        row = self.get(operator, suspension_id)
        if not is_open(row):
            raise conflict("that suspension has already been lifted")
        if dto.to_period < row.from_period:
            raise refuse("a suspension cannot lift before the period it started in")
        return self.store.suspensions.update(row.id, to_period=dto.to_period)

    def held_off(
        self, operator: Operator, employee_id: str, period: int, year_starts_on: str,
    ) -> list[str]:
        self.employees.get(operator, employee_id)
        return suspended_elements(self.store.suspensions.all(), employee_id, period,
                                  a_day(year_starts_on, "year_starts_on"))
