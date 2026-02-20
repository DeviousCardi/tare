"""Routes for premiums."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.premiums.schemas import (
    DefinePremium, ListPremiums, PremiumOut, UpliftOut,
)
from tare.modules.premiums.service import PremiumsService

router = APIRouter(prefix="/premiums", tags=["premiums"])


@router.get("")
def list_premiums(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    covering_hour: int | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = PremiumsService(store).list(operator, ListPremiums(
        employer_id=employer_id, covering_hour=covering_hour,
        limit=limit, offset=offset))
    return {"data": [PremiumOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/best")
def best_premium(
    employer_id: str, hour: int, on: str, operator: TheOperator, store: TheStore,
) -> PremiumOut:
    return PremiumOut.of(PremiumsService(store).best_for(operator, employer_id, hour, on))


@router.get("/{premium_id}/uplift")
def premium_uplift(
    premium_id: str, hourly_pay: int, hours: int,
    operator: TheOperator, store: TheStore,
) -> UpliftOut:
    return UpliftOut(**PremiumsService(store).uplift(
        operator, premium_id, hourly_pay, hours))


@router.get("/{premium_id}")
def get_premium(premium_id: str, operator: TheOperator, store: TheStore) -> PremiumOut:
    return PremiumOut.of(PremiumsService(store).get(operator, premium_id))


@router.post("", status_code=201)
def define_premium(
    dto: DefinePremium, operator: TheOperator, store: TheStore,
) -> PremiumOut:
    return PremiumOut.of(PremiumsService(store).define(operator, dto))
