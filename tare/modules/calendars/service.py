"""Pay calendars, and where a day falls in one."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, PayCalendar
from tare.modules.calendars.rules import (
    FREQUENCIES, PERIODS_A_YEAR, pay_day_for, period_holding, period_window, year_window,
)
from tare.modules.calendars.schemas import ListCalendars, OpenCalendar
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService


class CalendarsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListCalendars) -> dict:
        rows = visible_to(operator, self.store.calendars.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.frequency:
            rows = [row for row in rows if row.frequency == query.frequency]
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, calendar_id: str) -> PayCalendar:
        row = self.store.calendars.find(calendar_id)
        if not row:
            raise not_found("calendar", calendar_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def for_employer(self, operator: Operator, employer_id: str, day: str) -> PayCalendar:
        """The calendar covering a day for one employer."""
        self.employers.assert_visible(operator, employer_id)
        theirs = [row for row in self.store.calendars.all()
                  if row.employer_id == employer_id
                  and period_holding(row, a_day(day, "day")) is not None]
        if not theirs:
            raise not_found("calendar covering", f"{employer_id} on {day}")
        return theirs[0]

    def open(self, operator: Operator, dto: OpenCalendar) -> PayCalendar:
        self.employers.assert_visible(operator, dto.employer_id)
        if dto.frequency not in FREQUENCIES:
            raise refuse(f"{dto.frequency} is not a frequency this service runs")
        starts = a_day(dto.year_starts_on, "year_starts_on")
        clash = self.store.calendars.first(
            lambda row: row.employer_id == dto.employer_id
            and row.frequency == dto.frequency and row.year_starts_on == starts)
        if clash:
            raise conflict(f"a {dto.frequency} calendar already starts on {starts}")
        return self.store.calendars.insert(PayCalendar(
            id="", employer_id=dto.employer_id, frequency=dto.frequency,
            year_starts_on=starts,
            periods=dto.periods or PERIODS_A_YEAR[dto.frequency]))

    def period(self, operator: Operator, calendar_id: str, period: int) -> dict:
        row = self.get(operator, calendar_id)
        employer = self.employers.get(operator, row.employer_id)
        window = period_window(row, period)
        return {"calendar_id": row.id, "period": period, "start": window.start,
                "end": window.end, "pay_day": pay_day_for(row, period, employer.pay_day)}

    def holding(self, operator: Operator, calendar_id: str, day: str) -> int:
        row = self.get(operator, calendar_id)
        found = period_holding(row, a_day(day, "day"))
        if found is None:
            raise not_found("period holding", f"{day} in calendar {calendar_id}")
        return found

    def year(self, operator: Operator, calendar_id: str) -> dict:
        row = self.get(operator, calendar_id)
        window = year_window(row)
        return {"calendar_id": row.id, "start": window.start, "end": window.end}
