"""Routes for pay calendars."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.calendars.schemas import CalendarOut, ListCalendars, OpenCalendar, PeriodOut
from tare.modules.calendars.service import CalendarsService

router = APIRouter(prefix="/calendars", tags=["calendars"])


@router.get("")
def list_calendars(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    frequency: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = CalendarsService(store).list(operator, ListCalendars(
        employer_id=employer_id, frequency=frequency, limit=limit, offset=offset))
    return {"data": [CalendarOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{calendar_id}")
def get_calendar(calendar_id: str, operator: TheOperator, store: TheStore) -> CalendarOut:
    return CalendarOut.of(CalendarsService(store).get(operator, calendar_id))


@router.get("/{calendar_id}/year")
def calendar_year(calendar_id: str, operator: TheOperator, store: TheStore) -> dict:
    return CalendarsService(store).year(operator, calendar_id)


@router.get("/{calendar_id}/period/{period}")
def calendar_period(
    calendar_id: str, period: int, operator: TheOperator, store: TheStore,
) -> PeriodOut:
    return PeriodOut(**CalendarsService(store).period(operator, calendar_id, period))


@router.get("/{calendar_id}/holding/{day}")
def period_holding(calendar_id: str, day: str, operator: TheOperator, store: TheStore) -> dict:
    return {"calendar_id": calendar_id, "day": day,
            "period": CalendarsService(store).holding(operator, calendar_id, day)}


@router.post("", status_code=201)
def open_calendar(dto: OpenCalendar, operator: TheOperator, store: TheStore) -> CalendarOut:
    return CalendarOut.of(CalendarsService(store).open(operator, dto))
