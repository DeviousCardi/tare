"""Routes for rates."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.rates.schemas import AppliedOut, ListRates, RateOut, SetRate
from tare.modules.rates.service import RatesService

router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("")
def list_rates(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    element_id: str | None = Query(default=None),
    in_force_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = RatesService(store).list(operator, ListRates(
        employee_id=employee_id, element_id=element_id, in_force_on=in_force_on,
        limit=limit, offset=offset))
    return {"data": [RateOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/applied/{employee_id}")
def rate_applied(
    employee_id: str, element_id: str, on: str, hours: int,
    operator: TheOperator, store: TheStore,
) -> AppliedOut:
    return AppliedOut(**RatesService(store).applied(
        operator, employee_id, element_id, on, hours))


@router.get("/{rate_id}")
def get_rate(rate_id: str, operator: TheOperator, store: TheStore) -> RateOut:
    return RateOut.of(RatesService(store).get(operator, rate_id))


@router.post("", status_code=201)
def set_rate(dto: SetRate, operator: TheOperator, store: TheStore) -> RateOut:
    return RateOut.of(RatesService(store).set(operator, dto))
