"""Routes for levy codes."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.levycodes.schemas import (
    FreePayOut, LevyCodeOut, ListLevyCodes, PublishLevyCode,
)
from tare.modules.levycodes.service import LevyCodesService

router = APIRouter(prefix="/levy-codes", tags=["levy codes"])


@router.get("")
def list_levy_codes(
    operator: TheOperator, store: TheStore,
    code: str | None = Query(default=None),
    in_force_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = LevyCodesService(store).list(operator, ListLevyCodes(
        code=code, in_force_on=in_force_on, limit=limit, offset=offset))
    return {"data": [LevyCodeOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{code}/free-pay")
def free_pay(
    code: str, on: str, frequency: str, period: int,
    operator: TheOperator, store: TheStore,
) -> FreePayOut:
    return FreePayOut(**LevyCodesService(store).free_pay(code, on, frequency, period))


@router.get("/row/{levy_code_id}")
def get_levy_code(levy_code_id: str, operator: TheOperator, store: TheStore) -> LevyCodeOut:
    return LevyCodeOut.of(LevyCodesService(store).get(operator, levy_code_id))


@router.post("", status_code=201)
def publish_levy_code(
    dto: PublishLevyCode, operator: TheOperator, store: TheStore,
) -> LevyCodeOut:
    return LevyCodeOut.of(LevyCodesService(store).publish(operator, dto))
