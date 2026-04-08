"""The archive, and closing a run off into it."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau, visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import ArchiveEntry, Operator
from tare.modules.archive.rules import between, holds, sort_by_closed, totals_of
from tare.modules.archive.schemas import CloseOffRun, ListArchive
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.runs.service import RunsService


class ArchiveService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.runs = RunsService(store)

    def list(self, operator: Operator, query: ListArchive) -> dict:
        rows = visible_to(operator, self.store.archive.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.start and query.end:
            rows = between(rows, a_day(query.start, "start"), a_day(query.end, "end"))
        return page(sort_by_closed(rows), query.limit, query.offset)

    def get(self, operator: Operator, entry_id: str) -> ArchiveEntry:
        row = self.store.archive.find(entry_id)
        if not row:
            raise not_found("archive entry", entry_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def close_off(self, operator: Operator, dto: CloseOffRun) -> ArchiveEntry:
        assert_bureau(operator, "close a run off")
        run = self.runs.get(operator, dto.run_id)
        if run.status != "committed":
            raise refuse("only a committed run can be closed off")
        if holds(self.store.archive.all(), run.id):
            raise conflict("that run has already been closed off")
        closed_on = a_day(dto.closed_on, "closed_on")
        if run.committed_on and compare_dates(closed_on, run.committed_on) < 0:
            raise refuse("a run cannot be closed off before it was committed")
        slips = [row for row in self.store.payslips.all() if row.run_id == run.id]
        return self.store.archive.insert(ArchiveEntry(
            id="", employer_id=run.employer_id, run_id=run.id, closed_on=closed_on,
            payslips=len(slips), net=sum(row.net for row in slips)))

    def totals(self, operator: Operator) -> dict:
        return totals_of(visible_to(operator, self.store.archive.all()))

    def holds(self, operator: Operator, run_id: str) -> bool:
        return holds(visible_to(operator, self.store.archive.all()), run_id)
