"""Filings, and what the Revenue is owed for a period."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Filing, Operator
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.filings.rules import (
    days_to_go, due_on_for, is_late, owed_by, sort_by_period,
)
from tare.modules.filings.schemas import ListFilings, RaiseFiling
from tare.modules.runs.service import RunsService


class FilingsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.runs = RunsService(store)

    def list(self, operator: Operator, query: ListFilings) -> dict:
        rows = visible_to(operator, self.store.filings.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.period is not None:
            rows = [row for row in rows if row.period == query.period]
        return page(sort_by_period(rows), query.limit, query.offset)

    def get(self, operator: Operator, filing_id: str) -> Filing:
        row = self.store.filings.find(filing_id)
        if not row:
            raise not_found("filing", filing_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def raise_it(self, operator: Operator, dto: RaiseFiling) -> Filing:
        run = self.runs.get(operator, dto.run_id)
        if run.status != "committed":
            raise refuse("only a committed run has a return to make")
        if self.store.filings.first(lambda row: row.run_id == run.id):
            raise conflict("that run has already been filed")
        period_end = a_day(dto.period_end, "period_end")
        return self.store.filings.insert(Filing(
            id="", employer_id=run.employer_id, run_id=run.id, period=dto.period,
            period_end=period_end, due_on=due_on_for(period_end), gross=dto.gross,
            levy=dto.levy, contributions=dto.contributions))

    def state(self, operator: Operator, filing_id: str, on: str) -> dict:
        row = self.get(operator, filing_id)
        day = a_day(on, "on")
        return {"filing_id": row.id, "owed": owed_by(row), "due_on": row.due_on,
                "late": is_late(row, day), "days_to_go": days_to_go(row, day)}
