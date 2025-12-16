"""Routes for working patterns."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.patterns.schemas import (
    EndPattern, ExpectedOut, ListPatterns, PatternOut, SetPattern,
)
from tare.modules.patterns.service import PatternsService

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("")
def list_patterns(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    standing_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = PatternsService(store).list(operator, ListPatterns(
        employee_id=employee_id, standing_on=standing_on, limit=limit, offset=offset))
    return {"data": [PatternOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/standing/{employee_id}")
def standing_pattern(
    employee_id: str, on: str, operator: TheOperator, store: TheStore,
) -> PatternOut:
    return PatternOut.of(PatternsService(store).standing(operator, employee_id, on))


@router.get("/expected/{employee_id}")
def expected_hours(
    employee_id: str, start: str, end: str, operator: TheOperator, store: TheStore,
) -> ExpectedOut:
    return ExpectedOut(**PatternsService(store).expected(operator, employee_id, start, end))


@router.get("/overtime/{employee_id}")
def overtime(
    employee_id: str, on: str, worked: int, operator: TheOperator, store: TheStore,
) -> dict:
    service = PatternsService(store)
    return {"employee_id": employee_id, "on": on, "worked": worked,
            "weekly_hours": service.weekly(operator, employee_id, on),
            "overtime": service.overtime(operator, employee_id, on, worked)}


@router.get("/{pattern_id}")
def get_pattern(pattern_id: str, operator: TheOperator, store: TheStore) -> PatternOut:
    return PatternOut.of(PatternsService(store).get(operator, pattern_id))


@router.post("", status_code=201)
def set_pattern(dto: SetPattern, operator: TheOperator, store: TheStore) -> PatternOut:
    return PatternOut.of(PatternsService(store).set(operator, dto))


@router.post("/{pattern_id}/end")
def end_pattern(
    pattern_id: str, dto: EndPattern, operator: TheOperator, store: TheStore,
) -> PatternOut:
    return PatternOut.of(PatternsService(store).end(operator, pattern_id, dto))
