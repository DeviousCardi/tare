"""The people an employer pays, and who may look at them."""

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Employee, Operator
from tare.modules.employees.rules import in_post_on, next_reference, sort_by_name, sort_by_reference
from tare.modules.employees.schemas import (
    ChangeLevyCode, LeaveEmployee, ListEmployees, TakeOnEmployee,
)
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService


class EmployeesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListEmployees) -> dict:
        rows = visible_to(operator, self.store.employees.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.in_post_on:
            day = a_day(query.in_post_on, "in_post_on")
            rows = [row for row in rows if in_post_on(row, day)]
        rows = sort_by_name(rows) if query.by_name else sort_by_reference(rows)
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, employee_id: str) -> Employee:
        row = self.store.employees.find(employee_id)
        if not row:
            raise not_found("employee", employee_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def take_on(self, operator: Operator, dto: TakeOnEmployee) -> Employee:
        self.employers.assert_visible(operator, dto.employer_id)
        joined_on = a_day(dto.joined_on, "joined_on")
        born = a_day(dto.date_of_birth, "date_of_birth")
        reference = dto.reference or next_reference(
            self.store.employees.all(), dto.employer_id)
        if self.store.employees.first(lambda row: row.reference == reference):
            raise conflict(f"employee {reference} is already on the payroll")
        return self.store.employees.insert(Employee(
            id="", employer_id=dto.employer_id, reference=reference, name=dto.name,
            joined_on=joined_on, left_on=None, date_of_birth=born,
            levy_code=dto.levy_code))

    def leave(self, operator: Operator, employee_id: str, dto: LeaveEmployee) -> Employee:
        row = self.get(operator, employee_id)
        left_on = a_day(dto.left_on, "left_on")
        if row.left_on is not None:
            raise conflict(f"employee {row.reference} has already left")
        from tare.common.dates import compare_dates
        if compare_dates(left_on, row.joined_on) < 0:
            raise refuse("nobody can leave before they joined")
        return self.store.employees.update(row.id, left_on=left_on)

    def change_levy_code(
        self, operator: Operator, employee_id: str, dto: ChangeLevyCode,
    ) -> Employee:
        row = self.get(operator, employee_id)
        return self.store.employees.update(row.id, levy_code=dto.levy_code)
