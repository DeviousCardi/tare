"""The posts people hold."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Position
from tare.modules.costcentres.service import CostCentresService
from tare.modules.departments.service import DepartmentsService
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.positions.rules import headcount, held_by, held_on, sort_by_held_from
from tare.modules.positions.schemas import AppointToPosition, EndPosition, ListPositions


class PositionsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.departments = DepartmentsService(store)
        self.cost_centres = CostCentresService(store)

    def list(self, operator: Operator, query: ListPositions) -> dict:
        rows = visible_to(operator, self.store.positions.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.department_id:
            rows = [row for row in rows if row.department_id == query.department_id]
        if query.cost_centre_id:
            rows = [row for row in rows if row.cost_centre_id == query.cost_centre_id]
        if query.held_on:
            day = a_day(query.held_on, "held_on")
            rows = [row for row in rows if held_on(row, day)]
        return page(sort_by_held_from(rows), query.limit, query.offset)

    def get(self, operator: Operator, position_id: str) -> Position:
        row = self.store.positions.find(position_id)
        if not row:
            raise not_found("position", position_id)
        self.employees.get(operator, row.employee_id)
        return row

    def held(self, operator: Operator, employee_id: str, day: str) -> Position:
        self.employees.get(operator, employee_id)
        found = held_by(self.store.positions.all(), employee_id, a_day(day, "day"))
        if not found:
            raise not_found("position held", f"{employee_id} on {day}")
        return found

    def appoint(self, operator: Operator, dto: AppointToPosition) -> Position:
        person = self.employees.get(operator, dto.employee_id)
        held_from = a_day(dto.held_from, "held_from")
        department = self.departments.get(operator, dto.department_id)
        centre = self.cost_centres.get(operator, dto.cost_centre_id)
        if department.employer_id != person.employer_id:
            raise refuse("a post must sit in the person's own employer")
        if centre.employer_id != person.employer_id:
            raise refuse("a post must be booked to the person's own employer")
        if centre.closed:
            raise refuse(f"cost centre {centre.code} is closed and cannot take a post")
        if compare_dates(held_from, person.joined_on) < 0:
            raise refuse("a post cannot start before the person joined")
        if held_by(self.store.positions.all(), person.id, held_from):
            raise conflict(f"{person.reference} already holds a post on {held_from}")
        return self.store.positions.insert(Position(
            id="", employee_id=person.id, employer_id=person.employer_id,
            department_id=dto.department_id, cost_centre_id=dto.cost_centre_id,
            title=dto.title, held_from=held_from, held_to=None))

    def end(self, operator: Operator, position_id: str, dto: EndPosition) -> Position:
        row = self.get(operator, position_id)
        held_to = a_day(dto.held_to, "held_to")
        if row.held_to is not None:
            raise conflict("that post has already ended")
        if compare_dates(held_to, row.held_from) < 0:
            raise refuse("a post cannot end before it started")
        return self.store.positions.update(row.id, held_to=held_to)

    def headcount(self, operator: Operator, department_id: str, day: str) -> int:
        self.departments.get(operator, department_id)
        return headcount(self.store.positions.all(), department_id, a_day(day, "day"))
