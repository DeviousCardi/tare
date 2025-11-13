"""The Revenue's calendar. Everybody reads it; only the bureau publishes to it."""

from __future__ import annotations

from tare.common.dates import is_working_day
from tare.common.errors import conflict, not_found
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Holiday, Operator
from tare.modules.employers.schemas import a_day
from tare.modules.holidays.rules import between, days_of, in_year, sort_by_day
from tare.modules.holidays.schemas import ListHolidays, PublishHoliday


class HolidaysService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def days(self) -> list[str]:
        """The calendar as every date rule in the service wants it.

        No operator: the calendar is the Revenue's and it is the same for
        everybody, so narrowing it by employer would be inventing a rule.
        """
        return days_of(self.store.holidays.all())

    def list(self, operator: Operator, query: ListHolidays) -> dict:
        rows = sort_by_day(self.store.holidays.all())
        if query.year is not None:
            rows = in_year(rows, query.year)
        if query.start and query.end:
            rows = between(rows, a_day(query.start, "start"), a_day(query.end, "end"))
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, holiday_id: str) -> Holiday:
        row = self.store.holidays.find(holiday_id)
        if not row:
            raise not_found("holiday", holiday_id)
        return row

    def publish(self, operator: Operator, dto: PublishHoliday) -> Holiday:
        assert_bureau(operator, "publish a holiday")
        day = a_day(dto.holiday_on, "holiday_on")
        if self.store.holidays.first(lambda row: row.holiday_on == day):
            raise conflict(f"the calendar already holds {day}")
        return self.store.holidays.insert(Holiday(id="", holiday_on=day, name=dto.name))

    def withdraw(self, operator: Operator, holiday_id: str) -> None:
        assert_bureau(operator, "withdraw a holiday")
        self.get(operator, holiday_id)
        self.store.holidays.remove(holiday_id)

    def is_working_day(self, day: str) -> bool:
        return is_working_day(a_day(day, "day"), self.days())
