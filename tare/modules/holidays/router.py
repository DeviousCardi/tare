"""Routes for the Revenue's calendar."""

from fastapi import APIRouter, Query, Response

from tare.common.deps import TheOperator, TheStore
from tare.modules.holidays.schemas import (
    HolidayOut, ListHolidays, PublishHoliday, WorkingDayOut,
)
from tare.modules.holidays.service import HolidaysService

router = APIRouter(prefix="/holidays", tags=["holidays"])


@router.get("")
def list_holidays(
    operator: TheOperator, store: TheStore,
    year: int | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = HolidaysService(store).list(operator, ListHolidays(
        year=year, start=start, end=end, limit=limit, offset=offset))
    return {"data": [HolidayOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/working-day/{day}")
def working_day(day: str, operator: TheOperator, store: TheStore) -> WorkingDayOut:
    return WorkingDayOut(day=day, is_working_day=HolidaysService(store).is_working_day(day))


@router.get("/{holiday_id}")
def get_holiday(holiday_id: str, operator: TheOperator, store: TheStore) -> HolidayOut:
    return HolidayOut.of(HolidaysService(store).get(operator, holiday_id))


@router.post("", status_code=201)
def publish_holiday(dto: PublishHoliday, operator: TheOperator, store: TheStore) -> HolidayOut:
    return HolidayOut.of(HolidaysService(store).publish(operator, dto))


@router.delete("/{holiday_id}", status_code=204)
def withdraw_holiday(holiday_id: str, operator: TheOperator, store: TheStore) -> Response:
    HolidaysService(store).withdraw(operator, holiday_id)
    return Response(status_code=204)
