"""Routes for leave requests."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.leave.schemas import AskForLeave, DecideLeave, LeaveOut, ListLeave, TakenOut
from tare.modules.leave.service import LeaveService

router = APIRouter(prefix="/leave", tags=["leave"])


@router.get("")
def list_leave(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    covering: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = LeaveService(store).list(operator, ListLeave(
        employee_id=employee_id, status=status, covering=covering,
        limit=limit, offset=offset))
    return {"data": [LeaveOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/taken/{employee_id}")
def leave_taken(
    employee_id: str, start: str, end: str, operator: TheOperator, store: TheStore,
) -> TakenOut:
    return TakenOut(**LeaveService(store).taken(operator, employee_id, start, end))


@router.get("/{leave_id}")
def get_leave(leave_id: str, operator: TheOperator, store: TheStore) -> LeaveOut:
    return LeaveOut.of(LeaveService(store).get(operator, leave_id))


@router.get("/{leave_id}/days")
def leave_days(leave_id: str, operator: TheOperator, store: TheStore) -> dict:
    return {"leave_id": leave_id, "days": LeaveService(store).days(operator, leave_id)}


@router.post("", status_code=201)
def ask_for_leave(dto: AskForLeave, operator: TheOperator, store: TheStore) -> LeaveOut:
    return LeaveOut.of(LeaveService(store).ask(operator, dto))


@router.post("/{leave_id}/decide")
def decide_leave(
    leave_id: str, dto: DecideLeave, operator: TheOperator, store: TheStore,
) -> LeaveOut:
    return LeaveOut.of(LeaveService(store).decide(operator, leave_id, dto))
