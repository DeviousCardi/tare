"""Routes for departments."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.departments.schemas import (
    DepartmentOut, ListDepartments, MoveDepartment, OpenDepartment,
)
from tare.modules.departments.service import DepartmentsService

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("")
def list_departments(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    parent_id: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = DepartmentsService(store).list(operator, ListDepartments(
        employer_id=employer_id, parent_id=parent_id, limit=limit, offset=offset))
    return {"data": [DepartmentOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{department_id}")
def get_department(department_id: str, operator: TheOperator, store: TheStore) -> DepartmentOut:
    return DepartmentOut.of(DepartmentsService(store).get(operator, department_id))


@router.get("/{department_id}/children")
def department_children(department_id: str, operator: TheOperator, store: TheStore) -> dict:
    rows = DepartmentsService(store).children(operator, department_id)
    return {"data": [DepartmentOut.of(row) for row in rows], "total": len(rows)}


@router.get("/{department_id}/ancestors")
def department_ancestors(department_id: str, operator: TheOperator, store: TheStore) -> dict:
    rows = DepartmentsService(store).ancestors(operator, department_id)
    return {"data": [DepartmentOut.of(row) for row in rows], "total": len(rows)}


@router.post("", status_code=201)
def open_department(
    dto: OpenDepartment, operator: TheOperator, store: TheStore,
) -> DepartmentOut:
    return DepartmentOut.of(DepartmentsService(store).open(operator, dto))


@router.post("/{department_id}/move")
def move_department(
    department_id: str, dto: MoveDepartment, operator: TheOperator, store: TheStore,
) -> DepartmentOut:
    return DepartmentOut.of(DepartmentsService(store).move(operator, department_id, dto))
