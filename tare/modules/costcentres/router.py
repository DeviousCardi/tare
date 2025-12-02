"""Routes for cost centres."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from tare.common.deps import TheOperator, TheStore
from tare.modules.costcentres.schemas import (
    CloseCostCentre, CostCentreOut, ListCostCentres, OpenCostCentre, SpreadOut,
)
from tare.modules.costcentres.service import CostCentresService

router = APIRouter(prefix="/cost-centres", tags=["cost centres"])


class SpreadIn(BaseModel):
    amount: int
    centres: list[str]
    weights: list[int]


@router.get("")
def list_cost_centres(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    department_id: str | None = Query(default=None),
    bookable_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = CostCentresService(store).list(operator, ListCostCentres(
        employer_id=employer_id, department_id=department_id,
        bookable_only=bookable_only, limit=limit, offset=offset))
    return {"data": [CostCentreOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{cost_centre_id}")
def get_cost_centre(
    cost_centre_id: str, operator: TheOperator, store: TheStore,
) -> CostCentreOut:
    return CostCentreOut.of(CostCentresService(store).get(operator, cost_centre_id))


@router.post("", status_code=201)
def open_cost_centre(
    dto: OpenCostCentre, operator: TheOperator, store: TheStore,
) -> CostCentreOut:
    return CostCentreOut.of(CostCentresService(store).open(operator, dto))


@router.post("/{cost_centre_id}/close")
def close_cost_centre(
    cost_centre_id: str, dto: CloseCostCentre, operator: TheOperator, store: TheStore,
) -> CostCentreOut:
    return CostCentreOut.of(CostCentresService(store).close(operator, cost_centre_id, dto))


@router.post("/spread")
def spread_cost(dto: SpreadIn, operator: TheOperator, store: TheStore) -> SpreadOut:
    return SpreadOut(**CostCentresService(store).spread(
        operator, dto.amount, dto.centres, dto.weights))
