"""Leave requests, and what becomes of them."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import LeaveRequest, Operator
from tare.modules.employees.rules import in_post_on
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.holidays.service import HolidaysService
from tare.modules.leave.rules import (
    ASKED, STATUSES, clashes_with, covers, days_of, is_open, sort_by_start,
    taken_between,
)
from tare.modules.leave.schemas import AskForLeave, DecideLeave, ListLeave


class LeaveService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.holidays = HolidaysService(store)

    def list(self, operator: Operator, query: ListLeave) -> dict:
        rows = visible_to(operator, self.store.leave.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.status:
            rows = [row for row in rows if row.status == query.status]
        if query.covering:
            day = a_day(query.covering, "covering")
            rows = [row for row in rows if covers(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, leave_id: str) -> LeaveRequest:
        row = self.store.leave.find(leave_id)
        if not row:
            raise not_found("leave request", leave_id)
        self.employees.get(operator, row.employee_id)
        return row

    def ask(self, operator: Operator, dto: AskForLeave) -> LeaveRequest:
        person = self.employees.get(operator, dto.employee_id)
        starts_on = a_day(dto.starts_on, "starts_on")
        ends_on = a_day(dto.ends_on, "ends_on")
        asked_on = a_day(dto.asked_on, "asked_on")
        if compare_dates(ends_on, starts_on) < 0:
            raise refuse("leave cannot end before it starts")
        if compare_dates(starts_on, asked_on) < 0:
            raise refuse("leave cannot be asked for after it has started")
        if not in_post_on(person, starts_on):
            raise refuse(f"{person.reference} was not in post on {starts_on}")
        fresh = LeaveRequest(id="", employee_id=person.id,
                             employer_id=person.employer_id, starts_on=starts_on,
                             ends_on=ends_on, asked_on=asked_on, status=ASKED)
        for row in self.store.leave.all():
            if row.employee_id == person.id and clashes_with(row, fresh):
                raise conflict(f"{person.reference} already has leave across {row.starts_on}")
        return self.store.leave.insert(fresh)

    def decide(self, operator: Operator, leave_id: str, dto: DecideLeave) -> LeaveRequest:
        row = self.get(operator, leave_id)
        if dto.status not in STATUSES:
            raise refuse(f"{dto.status} is not something a request can become")
        if dto.status == ASKED:
            raise refuse("a request cannot be put back to waiting")
        if not is_open(row):
            raise conflict(f"that request was already {row.status}")
        return self.store.leave.update(row.id, status=dto.status)

    def days(self, operator: Operator, leave_id: str) -> int:
        return days_of(self.get(operator, leave_id), self.holidays.days())

    def taken(self, operator: Operator, employee_id: str, start: str, end: str) -> dict:
        self.employees.get(operator, employee_id)
        mine = [row for row in self.store.leave.all() if row.employee_id == employee_id]
        return {"employee_id": employee_id, "start": a_day(start, "start"),
                "end": a_day(end, "end"),
                "days": taken_between(mine, a_day(start, "start"), a_day(end, "end"),
                                      self.holidays.days())}
