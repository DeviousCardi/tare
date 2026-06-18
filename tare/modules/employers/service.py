"""Employers, and the visibility check the whole service leans on."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau, assert_sees
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Employer, Operator
from tare.modules.employers.rules import is_open_on, next_reference, sort_by_reference
from tare.modules.employers.schemas import CloseEmployer, ListEmployers, TakeOnEmployer, a_day


class EmployersService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def assert_visible(self, operator: Operator, employer_id: str) -> None:
        """The check every other area calls before it hands a row back.

        It resolves the employer as well as the operator, so a request naming an
        employer nobody has on the books is a 404 rather than a quiet empty
        listing that reads as "you have no people".
        """
        if not self.store.employers.find(employer_id):
            raise not_found("employer", employer_id)
        assert_sees(operator, employer_id)

    def list(self, operator: Operator, query: ListEmployers) -> dict:
        rows = sort_by_reference(self.store.employers.all())
        rows = [row for row in rows if operator.role == "bureau"
                or row.id == operator.employer_id]
        if query.open_on:
            day = a_day(query.open_on, "open_on")
            rows = [row for row in rows if is_open_on(row, day)]
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, employer_id: str) -> Employer:
        row = self.store.employers.find(employer_id)
        if not row:
            raise not_found("employer", employer_id)
        assert_sees(operator, employer_id)
        return row

    def take_on(self, operator: Operator, dto: TakeOnEmployer) -> Employer:
        assert_bureau(operator, "take on an employer")
        opened_on = a_day(dto.opened_on, "opened_on")
        reference = dto.reference or next_reference(self.store.employers.all())
        if self.store.employers.first(lambda row: row.reference == reference):
            raise conflict(f"employer {reference} is already on the books")
        return self.store.employers.insert(Employer(
            id="", reference=reference, name=dto.name, opened_on=opened_on,
            closed_on=None, pay_day=dto.pay_day))

    def close(self, operator: Operator, employer_id: str, dto: CloseEmployer) -> Employer:
        assert_bureau(operator, "close an employer")
        row = self.get(operator, employer_id)
        closed_on = a_day(dto.closed_on, "closed_on")
        if row.closed_on is not None:
            raise conflict(f"employer {row.reference} is already closed")
        if compare_dates(closed_on, row.opened_on) < 0:
            raise refuse("an employer cannot close before it was taken on")
        return self.store.employers.update(row.id, closed_on=closed_on)
