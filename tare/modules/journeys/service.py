"""Journeys, and what the miles come to."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Journey, Operator
from tare.modules.employees.rules import in_post_on
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.journeys.rules import (
    approved_only, between, miles_in, sort_by_travelled, worth_of,
)
from tare.modules.journeys.schemas import (
    ApproveJourney, ListJourneys, RecordJourney,
)


class JourneysService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListJourneys) -> dict:
        rows = visible_to(operator, self.store.journeys.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.start and query.end:
            rows = between(rows, a_day(query.start, "start"), a_day(query.end, "end"))
        if query.approved_only:
            rows = approved_only(rows)
        return page(sort_by_travelled(rows), query.limit, query.offset)

    def get(self, operator: Operator, journey_id: str) -> Journey:
        row = self.store.journeys.find(journey_id)
        if not row:
            raise not_found("journey", journey_id)
        self.employees.get(operator, row.employee_id)
        return row

    def record(self, operator: Operator, dto: RecordJourney) -> Journey:
        person = self.employees.get(operator, dto.employee_id)
        travelled_on = a_day(dto.travelled_on, "travelled_on")
        if not in_post_on(person, travelled_on):
            raise refuse(f"{person.reference} was not in post on {travelled_on}")
        return self.store.journeys.insert(Journey(
            id="", employee_id=person.id, employer_id=person.employer_id,
            travelled_on=travelled_on, miles=dto.miles, reason=dto.reason,
            approved=False))

    def approve(
        self, operator: Operator, journey_id: str, dto: ApproveJourney,
    ) -> Journey:
        row = self.get(operator, journey_id)
        if row.approved == dto.approved:
            raise conflict("that journey is already in the state it was asked for")
        return self.store.journeys.update(row.id, approved=dto.approved)

    def mileage(self, operator: Operator, employee_id: str, start: str,
                end: str, already: int = 0) -> dict:
        self.employees.get(operator, employee_id)
        first, last = a_day(start, "start"), a_day(end, "end")
        mine = [row for row in self.store.journeys.all()
                if row.employee_id == employee_id]
        miles = miles_in(mine, first, last)
        return {"employee_id": employee_id, "start": first, "end": last,
                "miles": miles, "worth": worth_of(miles, already)}
