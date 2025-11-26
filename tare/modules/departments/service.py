"""The parts an employer's organisation is divided into."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Department, Operator
from tare.modules.departments.rules import (
    ancestors_of, children_of, sort_by_code, would_make_a_cycle,
)
from tare.modules.departments.schemas import (
    ListDepartments, MoveDepartment, OpenDepartment,
)
from tare.modules.employers.service import EmployersService


class DepartmentsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListDepartments) -> dict:
        rows = visible_to(operator, self.store.departments.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.parent_id is not None:
            rows = [row for row in rows if row.parent_id == query.parent_id]
        return page(sort_by_code(rows), query.limit, query.offset)

    def get(self, operator: Operator, department_id: str) -> Department:
        row = self.store.departments.find(department_id)
        if not row:
            raise not_found("department", department_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def children(self, operator: Operator, department_id: str) -> list[Department]:
        self.get(operator, department_id)
        return children_of(self.store.departments.all(), department_id)

    def ancestors(self, operator: Operator, department_id: str) -> list[Department]:
        self.get(operator, department_id)
        return ancestors_of(self.store.departments.all(), department_id)

    def open(self, operator: Operator, dto: OpenDepartment) -> Department:
        self.employers.assert_visible(operator, dto.employer_id)
        if self.store.departments.first(
                lambda row: row.employer_id == dto.employer_id and row.code == dto.code):
            raise conflict(f"department {dto.code} already exists")
        if dto.parent_id:
            parent = self.get(operator, dto.parent_id)
            if parent.employer_id != dto.employer_id:
                raise refuse("a department cannot sit under another employer's")
        return self.store.departments.insert(Department(
            id="", employer_id=dto.employer_id, code=dto.code, name=dto.name,
            parent_id=dto.parent_id))

    def move(
        self, operator: Operator, department_id: str, dto: MoveDepartment,
    ) -> Department:
        row = self.get(operator, department_id)
        if dto.parent_id:
            parent = self.get(operator, dto.parent_id)
            if parent.employer_id != row.employer_id:
                raise refuse("a department cannot sit under another employer's")
            if would_make_a_cycle(self.store.departments.all(), row.id, dto.parent_id):
                raise refuse("that would fold the organisation onto itself")
        return self.store.departments.update(row.id, parent_id=dto.parent_id)
