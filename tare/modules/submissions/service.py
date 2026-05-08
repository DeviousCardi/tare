"""Submissions, and whether a filing has been settled."""

from __future__ import annotations

from tare.common.errors import not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Submission
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.filings.service import FilingsService
from tare.modules.submissions.rules import (
    attempts_on, is_settled, latest_for, sort_by_sent,
)
from tare.modules.submissions.schemas import ListSubmissions, SendSubmission


class SubmissionsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.filings = FilingsService(store)

    def list(self, operator: Operator, query: ListSubmissions) -> dict:
        rows = visible_to(operator, self.store.submissions.all())
        if query.filing_id:
            rows = [row for row in rows if row.filing_id == query.filing_id]
        if query.accepted_only:
            rows = [row for row in rows if row.accepted]
        return page(sort_by_sent(rows), query.limit, query.offset)

    def get(self, operator: Operator, submission_id: str) -> Submission:
        row = self.store.submissions.find(submission_id)
        if not row:
            raise not_found("submission", submission_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def send(self, operator: Operator, dto: SendSubmission) -> Submission:
        filing = self.filings.get(operator, dto.filing_id)
        if is_settled(self.store.submissions.all(), filing.id):
            raise refuse("that filing has already been taken")
        return self.store.submissions.insert(Submission(
            id="", filing_id=filing.id, employer_id=filing.employer_id,
            sent_on=a_day(dto.sent_on, "sent_on"), reference=dto.reference,
            accepted=dto.accepted, note=dto.note))

    def standing(self, operator: Operator, filing_id: str) -> dict:
        filing = self.filings.get(operator, filing_id)
        rows = self.store.submissions.all()
        latest = latest_for(rows, filing.id)
        return {"filing_id": filing.id, "attempts": attempts_on(rows, filing.id),
                "settled": is_settled(rows, filing.id),
                "standing_reference": latest.reference if latest else None}
