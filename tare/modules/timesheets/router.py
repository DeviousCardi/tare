"""Routes for timesheets."""

from fastapi import APIRouter, Query, Response

from tare.common.deps import TheOperator, TheStore
from tare.modules.timesheets.schemas import (
    ApproveLine, HoursOut, ListTimesheets, RecordHours, TimesheetOut,
)
from tare.modules.timesheets.service import TimesheetsService

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.get("")
def list_timesheets(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    approved_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = TimesheetsService(store).list(operator, ListTimesheets(
        employee_id=employee_id, start=start, end=end, approved_only=approved_only,
        limit=limit, offset=offset))
    return {"data": [TimesheetOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/hours/{employee_id}")
def hours(
    employee_id: str, start: str, end: str, operator: TheOperator, store: TheStore,
) -> HoursOut:
    return HoursOut(**TimesheetsService(store).hours(operator, employee_id, start, end))


@router.get("/{line_id}")
def get_line(line_id: str, operator: TheOperator, store: TheStore) -> TimesheetOut:
    return TimesheetOut.of(TimesheetsService(store).get(operator, line_id))


@router.post("", status_code=201)
def record_hours(dto: RecordHours, operator: TheOperator, store: TheStore) -> TimesheetOut:
    return TimesheetOut.of(TimesheetsService(store).record(operator, dto))


@router.post("/{line_id}/approve")
def approve_line(
    line_id: str, dto: ApproveLine, operator: TheOperator, store: TheStore,
) -> TimesheetOut:
    return TimesheetOut.of(TimesheetsService(store).approve(operator, line_id, dto))


@router.delete("/{line_id}", status_code=204)
def withdraw_line(line_id: str, operator: TheOperator, store: TheStore) -> Response:
    TimesheetsService(store).withdraw(operator, line_id)
    return Response(status_code=204)
