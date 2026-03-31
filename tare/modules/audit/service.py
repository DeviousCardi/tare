"""The audit trail. Everybody writes to it; nobody edits it."""

from __future__ import annotations

from tare.common.errors import not_found
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import AuditEntry, Operator
from tare.modules.audit.rules import between, sort_by_happened
from tare.modules.audit.schemas import ListEntries, RecordEntry
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService


class AuditService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def _mine(self, operator: Operator) -> list[AuditEntry]:
        """An entry against no employer is the bureau's own and stays with it."""
        if operator.role == "bureau":
            return self.store.audit.all()
        return [row for row in self.store.audit.all()
                if row.employer_id == operator.employer_id]

    def list(self, operator: Operator, query: ListEntries) -> dict:
        rows = self._mine(operator)
        if query.operator_id:
            rows = [row for row in rows if row.operator_id == query.operator_id]
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.action:
            rows = [row for row in rows if row.action == query.action]
        if query.start and query.end:
            rows = between(rows, a_day(query.start, "start"), a_day(query.end, "end"))
        return page(sort_by_happened(rows), query.limit, query.offset)

    def get(self, operator: Operator, entry_id: str) -> AuditEntry:
        row = self.store.audit.find(entry_id)
        if not row:
            raise not_found("audit entry", entry_id)
        if row.employer_id:
            self.employers.assert_visible(operator, row.employer_id)
        return row

    def record(self, operator: Operator, dto: RecordEntry) -> AuditEntry:
        if dto.employer_id:
            self.employers.assert_visible(operator, dto.employer_id)
        return self.store.audit.insert(AuditEntry(
            id="", operator_id=operator.id, operator_name=operator.name,
            employer_id=dto.employer_id, action=dto.action, subject=dto.subject,
            happened_on=a_day(dto.happened_on, "happened_on")))
