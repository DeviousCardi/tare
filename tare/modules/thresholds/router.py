"""Routes for the Revenue's thresholds."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.thresholds.schemas import (
    AgainstOut, ListThresholds, PublishThreshold, ThresholdOut,
)
from tare.modules.thresholds.service import ThresholdsService

router = APIRouter(prefix="/thresholds", tags=["thresholds"])


@router.get("")
def list_thresholds(
    operator: TheOperator, store: TheStore,
    kind: str | None = Query(default=None),
    frequency: str | None = Query(default=None),
    in_force_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ThresholdsService(store).list(operator, ListThresholds(
        kind=kind, frequency=frequency, in_force_on=in_force_on,
        limit=limit, offset=offset))
    return {"data": [ThresholdOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{kind}/against")
def against(
    kind: str, frequency: str, on: str, amount: int,
    operator: TheOperator, store: TheStore,
) -> AgainstOut:
    return AgainstOut(**ThresholdsService(store).against(kind, frequency, on, amount))


@router.get("/row/{threshold_id}")
def get_threshold(threshold_id: str, operator: TheOperator, store: TheStore) -> ThresholdOut:
    return ThresholdOut.of(ThresholdsService(store).get(operator, threshold_id))


@router.post("", status_code=201)
def publish_threshold(
    dto: PublishThreshold, operator: TheOperator, store: TheStore,
) -> ThresholdOut:
    return ThresholdOut.of(ThresholdsService(store).publish(operator, dto))
