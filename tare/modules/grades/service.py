"""Grades, and the points each covers."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Grade, Operator
from tare.modules.employers.service import EmployersService
from tare.modules.grades.rules import covers, grade_holding, points_covered, sort_by_code
from tare.modules.grades.schemas import DefineGrade, ListGrades
from tare.modules.scales.service import ScalesService


class GradesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.scales = ScalesService(store)

    def list(self, operator: Operator, query: ListGrades) -> dict:
        rows = visible_to(operator, self.store.grades.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.scale_code:
            rows = [row for row in rows if row.scale_code == query.scale_code]
        return page(sort_by_code(rows), query.limit, query.offset)

    def get(self, operator: Operator, grade_id: str) -> Grade:
        row = self.store.grades.find(grade_id)
        if not row:
            raise not_found("grade", grade_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def define(self, operator: Operator, dto: DefineGrade) -> Grade:
        self.employers.assert_visible(operator, dto.employer_id)
        if dto.highest_point <= dto.lowest_point:
            raise refuse("a grade must reach above the point it starts at")
        if self.store.grades.first(
                lambda row: row.employer_id == dto.employer_id and row.code == dto.code):
            raise conflict(f"grade {dto.code} already exists")
        return self.store.grades.insert(Grade(
            id="", employer_id=dto.employer_id, code=dto.code, name=dto.name,
            scale_code=dto.scale_code, lowest_point=dto.lowest_point,
            highest_point=dto.highest_point))

    def points(self, operator: Operator, grade_id: str) -> list[int]:
        return points_covered(self.get(operator, grade_id))

    def holds(self, operator: Operator, grade_id: str, point: int) -> bool:
        return covers(self.get(operator, grade_id), point)

    def holding(
        self, operator: Operator, employer_id: str, scale_code: str, point: int,
    ) -> Grade:
        self.employers.assert_visible(operator, employer_id)
        mine = [row for row in self.store.grades.all()
                if row.employer_id == employer_id]
        found = grade_holding(mine, scale_code, point)
        if not found:
            raise not_found("grade covering", f"{scale_code} point {point}")
        return found

    def salary(self, operator: Operator, grade_id: str, point: int, day: str) -> int:
        row = self.get(operator, grade_id)
        if not covers(row, point):
            raise refuse(f"grade {row.code} does not cover point {point}")
        return self.scales.value(row.scale_code, point, day)
