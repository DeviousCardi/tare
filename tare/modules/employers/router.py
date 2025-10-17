"""Routes for employers."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.employers.schemas import (
    CloseEmployer, EmployerOut, ListEmployers, TakeOnEmployer,
)
from tare.modules.employers.service import EmployersService

router = APIRouter(prefix="/employers", tags=["employers"])


@router.get("")
def list_employers(
    operator: TheOperator, store: TheStore,
    open_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = EmployersService(store).list(
        operator, ListEmployers(open_on=open_on, limit=limit, offset=offset))
    return {"data": [EmployerOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{employer_id}")
def get_employer(employer_id: str, operator: TheOperator, store: TheStore) -> EmployerOut:
    return EmployerOut.of(EmployersService(store).get(operator, employer_id))


@router.post("", status_code=201)
def take_on_employer(dto: TakeOnEmployer, operator: TheOperator, store: TheStore) -> EmployerOut:
    return EmployerOut.of(EmployersService(store).take_on(operator, dto))


@router.post("/{employer_id}/close")
def close_employer(
    employer_id: str, dto: CloseEmployer, operator: TheOperator, store: TheStore,
) -> EmployerOut:
    return EmployerOut.of(EmployersService(store).close(operator, employer_id, dto))
