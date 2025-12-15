"""Routes for grades."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.grades.schemas import DefineGrade, GradeOut, ListGrades
from tare.modules.grades.service import GradesService

router = APIRouter(prefix="/grades", tags=["grades"])


@router.get("")
def list_grades(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    scale_code: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = GradesService(store).list(operator, ListGrades(
        employer_id=employer_id, scale_code=scale_code, limit=limit, offset=offset))
    return {"data": [GradeOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/holding")
def grade_holding(
    employer_id: str, scale_code: str, point: int,
    operator: TheOperator, store: TheStore,
) -> GradeOut:
    return GradeOut.of(GradesService(store).holding(
        operator, employer_id, scale_code, point))


@router.get("/{grade_id}")
def get_grade(grade_id: str, operator: TheOperator, store: TheStore) -> GradeOut:
    return GradeOut.of(GradesService(store).get(operator, grade_id))


@router.get("/{grade_id}/points")
def grade_points(grade_id: str, operator: TheOperator, store: TheStore) -> dict:
    return {"grade_id": grade_id, "points": GradesService(store).points(operator, grade_id)}


@router.get("/{grade_id}/salary/{point}")
def grade_salary(
    grade_id: str, point: int, on: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"grade_id": grade_id, "point": point, "on": on,
            "annual_salary": GradesService(store).salary(operator, grade_id, point, on)}


@router.post("", status_code=201)
def define_grade(dto: DefineGrade, operator: TheOperator, store: TheStore) -> GradeOut:
    return GradeOut.of(GradesService(store).define(operator, dto))
