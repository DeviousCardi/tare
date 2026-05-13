"""Year-end statements, drawn from the payslips behind them."""

from __future__ import annotations

from tare.common.dates import within_window
from tare.common.errors import conflict, not_found
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, YearEndStatement
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.statements.rules import (
    agrees_with, is_issued, sort_by_year, totals_from,
)
from tare.modules.statements.schemas import (
    DrawStatement, IssueStatement, ListStatements,
)


class StatementsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def _slips(self, employee_id: str, start: str, end: str) -> list:
        return [row for row in self.store.payslips.all()
                if row.employee_id == employee_id
                and within_window(row.end, start, end)]

    def list(self, operator: Operator, query: ListStatements) -> dict:
        rows = visible_to(operator, self.store.statements.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.year_starts_on:
            starts = a_day(query.year_starts_on, "year_starts_on")
            rows = [row for row in rows if row.year_starts_on == starts]
        if query.issued_only:
            rows = [row for row in rows if is_issued(row)]
        return page(sort_by_year(rows), query.limit, query.offset)

    def get(self, operator: Operator, statement_id: str) -> YearEndStatement:
        row = self.store.statements.find(statement_id)
        if not row:
            raise not_found("statement", statement_id)
        self.employees.get(operator, row.employee_id)
        return row

    def draw(self, operator: Operator, dto: DrawStatement) -> YearEndStatement:
        person = self.employees.get(operator, dto.employee_id)
        starts = a_day(dto.year_starts_on, "year_starts_on")
        ends = a_day(dto.year_ends_on, "year_ends_on")
        clash = self.store.statements.first(
            lambda row: row.employee_id == person.id and row.year_starts_on == starts)
        if clash:
            raise conflict(f"{person.reference} already has a statement for that year")
        totals = totals_from(self._slips(person.id, starts, ends))
        return self.store.statements.insert(YearEndStatement(
            id="", employee_id=person.id, employer_id=person.employer_id,
            year_starts_on=starts, year_ends_on=ends, issued_on=None, **totals))

    def issue(
        self, operator: Operator, statement_id: str, dto: IssueStatement,
    ) -> YearEndStatement:
        row = self.get(operator, statement_id)
        if is_issued(row):
            raise conflict("that statement has already been issued")
        return self.store.statements.update(
            row.id, issued_on=a_day(dto.issued_on, "issued_on"))

    def agrees(self, operator: Operator, statement_id: str) -> bool:
        row = self.get(operator, statement_id)
        return agrees_with(row, self._slips(row.employee_id, row.year_starts_on,
                                            row.year_ends_on))
