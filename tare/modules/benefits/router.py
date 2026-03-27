"""Routes for benefit awards."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.benefits.schemas import (
    AwardBenefit, BenefitOut, BenefitValueOut, EndBenefit, ListBenefits,
)
from tare.modules.benefits.service import BenefitsService

router = APIRouter(prefix="/benefits", tags=["benefits"])


@router.get("")
def list_benefits(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    class_id: str | None = Query(default=None),
    held_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = BenefitsService(store).list(operator, ListBenefits(
        employee_id=employee_id, class_id=class_id, held_on=held_on,
        limit=limit, offset=offset))
    return {"data": [BenefitOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{award_id}")
def get_benefit(award_id: str, operator: TheOperator, store: TheStore) -> BenefitOut:
    return BenefitOut.of(BenefitsService(store).get(operator, award_id))


@router.get("/{award_id}/value")
def benefit_value(
    award_id: str, days: int, operator: TheOperator, store: TheStore,
) -> BenefitValueOut:
    return BenefitValueOut(**BenefitsService(store).value(operator, award_id, days))


@router.post("", status_code=201)
def award_benefit(dto: AwardBenefit, operator: TheOperator, store: TheStore) -> BenefitOut:
    return BenefitOut.of(BenefitsService(store).award(operator, dto))


@router.post("/{award_id}/end")
def end_benefit(
    award_id: str, dto: EndBenefit, operator: TheOperator, store: TheStore,
) -> BenefitOut:
    return BenefitOut.of(BenefitsService(store).end(operator, award_id, dto))
