"""Working patterns, and what they expect of somebody."""

from __future__ import annotations

from tare.common.dates import add_days, compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, WorkingPattern
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.patterns.rules import (
    expected_between, hours_on, overtime_above, sort_by_start, standing_for, stands_on,
    weekly_hours,
)
from tare.modules.patterns.schemas import EndPattern, ListPatterns, SetPattern


class PatternsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListPatterns) -> dict:
        rows = visible_to(operator, self.store.patterns.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.standing_on:
            day = a_day(query.standing_on, "standing_on")
            rows = [row for row in rows if stands_on(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, pattern_id: str) -> WorkingPattern:
        row = self.store.patterns.find(pattern_id)
        if not row:
            raise not_found("pattern", pattern_id)
        self.employees.get(operator, row.employee_id)
        return row

    def standing(self, operator: Operator, employee_id: str, day: str) -> WorkingPattern:
        self.employees.get(operator, employee_id)
        found = standing_for(self.store.patterns.all(), employee_id, a_day(day, "day"))
        if not found:
            raise not_found("pattern standing", f"{employee_id} on {day}")
        return found

    def set(self, operator: Operator, dto: SetPattern) -> WorkingPattern:
        """Put somebody on a new pattern, ending whatever stood the day before."""
        person = self.employees.get(operator, dto.employee_id)
        starts_on = a_day(dto.starts_on, "starts_on")
        if any(hours < 0 or hours > 24 for hours in dto.hours):
            raise refuse("a day cannot hold fewer than no hours or more than 24")
        if compare_dates(starts_on, person.joined_on) < 0:
            raise refuse("a pattern cannot start before the person joined")
        standing = standing_for(self.store.patterns.all(), person.id, starts_on)
        if standing:
            if standing.starts_on == starts_on:
                raise conflict(f"a pattern already starts on {starts_on}")
            self.store.patterns.update(standing.id, ends_on=add_days(starts_on, -1))
        return self.store.patterns.insert(WorkingPattern(
            id="", employee_id=person.id, employer_id=person.employer_id,
            starts_on=starts_on, ends_on=None, hours=list(dto.hours)))

    def end(self, operator: Operator, pattern_id: str, dto: EndPattern) -> WorkingPattern:
        row = self.get(operator, pattern_id)
        ends_on = a_day(dto.ends_on, "ends_on")
        if row.ends_on is not None:
            raise conflict("that pattern has already ended")
        if compare_dates(ends_on, row.starts_on) < 0:
            raise refuse("a pattern cannot end before it starts")
        return self.store.patterns.update(row.id, ends_on=ends_on)

    def expected(self, operator: Operator, employee_id: str, start: str, end: str) -> dict:
        row = self.standing(operator, employee_id, start)
        hours = expected_between(row, a_day(start, "start"), a_day(end, "end"))
        return {"employee_id": employee_id, "start": start, "end": end, "hours": hours}

    def overtime(self, operator: Operator, employee_id: str, day: str, worked: int) -> int:
        return overtime_above(self.standing(operator, employee_id, day), worked)

    def hours_on(self, operator: Operator, employee_id: str, day: str) -> int:
        return hours_on(self.standing(operator, employee_id, day), a_day(day, "day"))

    def weekly(self, operator: Operator, employee_id: str, day: str) -> int:
        return weekly_hours(self.standing(operator, employee_id, day))
