"""Routes for the audit trail."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.audit.schemas import EntryOut, ListEntries, RecordEntry
from tare.modules.audit.service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_entries(
    operator: TheOperator, store: TheStore,
    operator_id: str | None = Query(default=None),
    employer_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = AuditService(store).list(operator, ListEntries(
        operator_id=operator_id, employer_id=employer_id, action=action,
        start=start, end=end, limit=limit, offset=offset))
    return {"data": [EntryOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{entry_id}")
def get_entry(entry_id: str, operator: TheOperator, store: TheStore) -> EntryOut:
    return EntryOut.of(AuditService(store).get(operator, entry_id))


@router.post("", status_code=201)
def record_entry(dto: RecordEntry, operator: TheOperator, store: TheStore) -> EntryOut:
    return EntryOut.of(AuditService(store).record(operator, dto))
