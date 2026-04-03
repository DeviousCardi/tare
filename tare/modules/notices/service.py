"""Notices, and getting them out of the door."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Notice, Operator
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.notices.rules import KINDS, is_late, is_waiting, sort_by_raised, waiting
from tare.modules.notices.schemas import ListNotices, RaiseNotice, SendNotice


class NoticesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListNotices) -> dict:
        rows = visible_to(operator, self.store.notices.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.kind:
            rows = [row for row in rows if row.kind == query.kind]
        if query.waiting_only:
            rows = waiting(rows)
        return page(sort_by_raised(rows), query.limit, query.offset)

    def get(self, operator: Operator, notice_id: str) -> Notice:
        row = self.store.notices.find(notice_id)
        if not row:
            raise not_found("notice", notice_id)
        self.employees.get(operator, row.employee_id)
        return row

    def raise_it(self, operator: Operator, dto: RaiseNotice) -> Notice:
        person = self.employees.get(operator, dto.employee_id)
        if dto.kind not in KINDS:
            raise refuse(f"{dto.kind} is not something the bureau writes about")
        return self.store.notices.insert(Notice(
            id="", employee_id=person.id, employer_id=person.employer_id,
            kind=dto.kind, subject=dto.subject,
            raised_on=a_day(dto.raised_on, "raised_on"), sent_on=None))

    def send(self, operator: Operator, notice_id: str, dto: SendNotice) -> Notice:
        row = self.get(operator, notice_id)
        if not is_waiting(row):
            raise conflict("that notice has already gone out")
        sent_on = a_day(dto.sent_on, "sent_on")
        if compare_dates(sent_on, row.raised_on) < 0:
            raise refuse("a notice cannot go out before it was raised")
        return self.store.notices.update(row.id, sent_on=sent_on)

    def late(self, operator: Operator, upto: str) -> list[Notice]:
        day = a_day(upto, "upto")
        return [row for row in waiting(visible_to(operator, self.store.notices.all()))
                if is_late(row, day)]
