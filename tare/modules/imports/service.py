"""Import batches, and whether they are fit to apply."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import ImportBatch, Operator
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.imports.rules import (
    ACCEPTED, KINDS, RECEIVED, STATUSES, between, is_fit, is_open, readable_share,
    rows_missed, sort_by_received,
)
from tare.modules.imports.schemas import DecideBatch, ListBatches, ReceiveBatch


class ImportsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListBatches) -> dict:
        rows = visible_to(operator, self.store.imports.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.kind:
            rows = [row for row in rows if row.kind == query.kind]
        if query.open_only:
            rows = [row for row in rows if is_open(row)]
        if query.start and query.end:
            rows = between(rows, a_day(query.start, "start"), a_day(query.end, "end"))
        return page(sort_by_received(rows), query.limit, query.offset)

    def get(self, operator: Operator, batch_id: str) -> ImportBatch:
        row = self.store.imports.find(batch_id)
        if not row:
            raise not_found("batch", batch_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def receive(self, operator: Operator, dto: ReceiveBatch) -> ImportBatch:
        self.employers.assert_visible(operator, dto.employer_id)
        if dto.kind not in KINDS:
            raise refuse(f"{dto.kind} is not something an employer pushes across")
        if dto.rows_read > dto.rows_offered:
            raise refuse("a batch cannot read more rows than it holds")
        if self.store.imports.first(lambda row: row.reference == dto.reference):
            raise conflict(f"batch {dto.reference} has already been received")
        return self.store.imports.insert(ImportBatch(
            id="", employer_id=dto.employer_id, kind=dto.kind,
            reference=dto.reference,
            received_on=a_day(dto.received_on, "received_on"),
            rows_offered=dto.rows_offered, rows_read=dto.rows_read,
            status=RECEIVED))

    def decide(self, operator: Operator, batch_id: str, dto: DecideBatch) -> ImportBatch:
        row = self.get(operator, batch_id)
        if dto.status not in STATUSES:
            raise refuse(f"{dto.status} is not something a batch can become")
        if dto.status == RECEIVED:
            raise refuse("a batch cannot be put back to waiting")
        if not is_open(row):
            raise conflict(f"that batch was already {row.status}")
        if dto.status == ACCEPTED and not is_fit(row):
            raise refuse("too little of that batch came through to apply it")
        return self.store.imports.update(row.id, status=dto.status)

    def state(self, operator: Operator, batch_id: str) -> dict:
        row = self.get(operator, batch_id)
        return {"batch_id": row.id, "readable_share": readable_share(row),
                "rows_missed": rows_missed(row), "fit": is_fit(row)}
