"""Routes for the people an employer pays."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.employees.schemas import (
    ChangeLevyCode, EmployeeOut, LeaveEmployee, ListEmployees, TakeOnEmployee,
)
from tare.modules.employees.service import EmployeesService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("")
def list_employees(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    in_post_on: str | None = Query(default=None),
    by_name: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = EmployeesService(store).list(operator, ListEmployees(
        employer_id=employer_id, in_post_on=in_post_on, by_name=by_name,
        limit=limit, offset=offset))
    return {"data": [EmployeeOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{employee_id}")
def get_employee(employee_id: str, operator: TheOperator, store: TheStore) -> EmployeeOut:
    return EmployeeOut.of(EmployeesService(store).get(operator, employee_id))


@router.post("", status_code=201)
def take_on_employee(dto: TakeOnEmployee, operator: TheOperator, store: TheStore) -> EmployeeOut:
    return EmployeeOut.of(EmployeesService(store).take_on(operator, dto))


@router.post("/{employee_id}/leave")
def leave_employee(
    employee_id: str, dto: LeaveEmployee, operator: TheOperator, store: TheStore,
) -> EmployeeOut:
    return EmployeeOut.of(EmployeesService(store).leave(operator, employee_id, dto))


@router.post("/{employee_id}/levy-code")
def change_levy_code(
    employee_id: str, dto: ChangeLevyCode, operator: TheOperator, store: TheStore,
) -> EmployeeOut:
    return EmployeeOut.of(EmployeesService(store).change_levy_code(operator, employee_id, dto))
