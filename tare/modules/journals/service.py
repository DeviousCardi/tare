"""Journals, and posting a run to the ledger."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import JournalLine, Operator
from tare.modules.journals.rules import (
    balances, credits_of, debits_of, postings_for, sort_by_account,
)
from tare.modules.journals.schemas import ListJournal, PostRun
from tare.modules.runs.service import RunsService


class JournalsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.runs = RunsService(store)

    def list(self, operator: Operator, query: ListJournal) -> dict:
        rows = visible_to(operator, self.store.journals.all())
        if query.run_id:
            rows = [row for row in rows if row.run_id == query.run_id]
        if query.account:
            rows = [row for row in rows if row.account == query.account]
        return page(sort_by_account(rows), query.limit, query.offset)

    def get(self, operator: Operator, line_id: str) -> JournalLine:
        row = self.store.journals.find(line_id)
        if not row:
            raise not_found("journal line", line_id)
        from tare.modules.employers.service import EmployersService

        EmployersService(self.store).assert_visible(operator, row.employer_id)
        return row

    def post(self, operator: Operator, dto: PostRun) -> dict:
        run = self.runs.get(operator, dto.run_id)
        if run.status != "committed":
            raise refuse("only a committed run can be posted")
        if self.store.journals.first(lambda row: row.run_id == run.id):
            raise conflict("that run has already been posted")
        slips = [row for row in self.store.payslips.all() if row.run_id == run.id]
        for posting in postings_for(slips):
            self.store.journals.insert(JournalLine(
                id="", run_id=run.id, employer_id=run.employer_id,
                account=posting.account, cost_centre_id=posting.cost_centre_id,
                debit=posting.debit, credit=posting.credit,
                narrative=posting.narrative))
        return self.of(operator, run.id)

    def of(self, operator: Operator, run_id: str) -> dict:
        run = self.runs.get(operator, run_id)
        rows = sort_by_account([row for row in self.store.journals.all()
                                if row.run_id == run.id])
        return {"run_id": run.id, "lines": rows, "debits": debits_of(rows),
                "credits": credits_of(rows), "balances": balances(rows)}
