"""Accruals, and what somebody has earned so far."""

from __future__ import annotations

from tare.common.errors import conflict, not_found
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import LeaveAccrual, Operator
from tare.modules.accruals.rules import (
    as_days, earned_by, earned_in_year, sort_by_period, worked_in_year,
)
from tare.modules.accruals.schemas import ListAccruals, RecordAccrual
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day


class AccrualsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListAccruals) -> dict:
        rows = visible_to(operator, self.store.accruals.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.year_starts_on:
            starts = a_day(query.year_starts_on, "year_starts_on")
            rows = [row for row in rows if row.year_starts_on == starts]
        return page(sort_by_period(rows), query.limit, query.offset)

    def get(self, operator: Operator, accrual_id: str) -> LeaveAccrual:
        row = self.store.accruals.find(accrual_id)
        if not row:
            raise not_found("accrual", accrual_id)
        self.employees.get(operator, row.employee_id)
        return row

    def record(self, operator: Operator, dto: RecordAccrual) -> LeaveAccrual:
        person = self.employees.get(operator, dto.employee_id)
        starts = a_day(dto.year_starts_on, "year_starts_on")
        clash = self.store.accruals.first(
            lambda row: row.employee_id == person.id
            and row.year_starts_on == starts and row.period == dto.period)
        if clash:
            raise conflict(
                f"{person.reference} already has an accrual for period {dto.period}")
        return self.store.accruals.insert(LeaveAccrual(
            id="", employee_id=person.id, employer_id=person.employer_id,
            year_starts_on=starts, period=dto.period,
            hours_worked=dto.hours_worked, hours_earned=earned_by(dto.hours_worked)))

    def earned(self, operator: Operator, employee_id: str,
               year_starts_on: str) -> dict:
        self.employees.get(operator, employee_id)
        starts = a_day(year_starts_on, "year_starts_on")
        rows = self.store.accruals.all()
        hours = earned_in_year(rows, employee_id, starts)
        return {"employee_id": employee_id, "year_starts_on": starts,
                "hours_worked": worked_in_year(rows, employee_id, starts),
                "hours_earned": hours, "days_earned": as_days(hours)}
