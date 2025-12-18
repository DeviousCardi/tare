"""Timesheets, and what a window of them comes to."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, TimesheetLine
from tare.modules.elements.service import ElementsService
from tare.modules.employees.rules import in_post_on
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.timesheets.rules import (
    approved_only, between, days_worked, hours_between, hours_by_element, sort_by_day,
)
from tare.modules.timesheets.schemas import ApproveLine, ListTimesheets, RecordHours


class TimesheetsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.elements = ElementsService(store)

    def list(self, operator: Operator, query: ListTimesheets) -> dict:
        rows = visible_to(operator, self.store.timesheets.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.start and query.end:
            rows = between(rows, a_day(query.start, "start"), a_day(query.end, "end"))
        if query.approved_only:
            rows = approved_only(rows)
        return page(sort_by_day(rows), query.limit, query.offset)

    def get(self, operator: Operator, line_id: str) -> TimesheetLine:
        row = self.store.timesheets.find(line_id)
        if not row:
            raise not_found("timesheet line", line_id)
        self.employees.get(operator, row.employee_id)
        return row

    def record(self, operator: Operator, dto: RecordHours) -> TimesheetLine:
        person = self.employees.get(operator, dto.employee_id)
        worked_on = a_day(dto.worked_on, "worked_on")
        element = self.elements.get(operator, dto.element_id)
        if element.employer_id != person.employer_id:
            raise refuse("hours must be paid as an element of the person's own employer")
        if element.kind != "payment":
            raise refuse("hours cannot be recorded against a deduction")
        if not in_post_on(person, worked_on):
            raise refuse(f"{person.reference} was not in post on {worked_on}")
        clash = self.store.timesheets.first(
            lambda row: row.employee_id == person.id and row.worked_on == worked_on
            and row.element_id == dto.element_id)
        if clash:
            raise conflict(
                f"{person.reference} already has {element.code} hours on {worked_on}")
        return self.store.timesheets.insert(TimesheetLine(
            id="", employee_id=person.id, employer_id=person.employer_id,
            worked_on=worked_on, hours=dto.hours, element_id=dto.element_id,
            approved=False))

    def approve(self, operator: Operator, line_id: str, dto: ApproveLine) -> TimesheetLine:
        row = self.get(operator, line_id)
        if row.approved == dto.approved:
            raise conflict("that line is already in the state it was asked for")
        return self.store.timesheets.update(row.id, approved=dto.approved)

    def withdraw(self, operator: Operator, line_id: str) -> None:
        row = self.get(operator, line_id)
        if row.approved:
            raise refuse("an approved line cannot be withdrawn")
        self.store.timesheets.remove(row.id)

    def hours(self, operator: Operator, employee_id: str, start: str, end: str) -> dict:
        self.employees.get(operator, employee_id)
        first, last = a_day(start, "start"), a_day(end, "end")
        mine = [row for row in self.store.timesheets.all()
                if row.employee_id == employee_id]
        return {"employee_id": employee_id, "start": first, "end": last,
                "hours": hours_between(mine, first, last),
                "days_worked": days_worked(mine, first, last),
                "by_element": hours_by_element(mine, first, last)}
