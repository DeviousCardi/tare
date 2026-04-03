"""Routes for notices."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.notices.schemas import ListNotices, NoticeOut, RaiseNotice, SendNotice
from tare.modules.notices.service import NoticesService

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("")
def list_notices(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    waiting_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = NoticesService(store).list(operator, ListNotices(
        employee_id=employee_id, kind=kind, waiting_only=waiting_only,
        limit=limit, offset=offset))
    return {"data": [NoticeOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/late")
def late_notices(on: str, operator: TheOperator, store: TheStore) -> dict:
    rows = NoticesService(store).late(operator, on)
    return {"on": on, "data": [NoticeOut.of(row) for row in rows], "total": len(rows)}


@router.get("/{notice_id}")
def get_notice(notice_id: str, operator: TheOperator, store: TheStore) -> NoticeOut:
    return NoticeOut.of(NoticesService(store).get(operator, notice_id))


@router.post("", status_code=201)
def raise_notice(dto: RaiseNotice, operator: TheOperator, store: TheStore) -> NoticeOut:
    return NoticeOut.of(NoticesService(store).raise_it(operator, dto))


@router.post("/{notice_id}/send")
def send_notice(
    notice_id: str, dto: SendNotice, operator: TheOperator, store: TheStore,
) -> NoticeOut:
    return NoticeOut.of(NoticesService(store).send(operator, notice_id, dto))
