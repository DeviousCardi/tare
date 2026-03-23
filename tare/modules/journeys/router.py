"""Routes for journeys."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.journeys.schemas import (
    ApproveJourney, JourneyOut, ListJourneys, MileageOut, RecordJourney,
)
from tare.modules.journeys.service import JourneysService

router = APIRouter(prefix="/journeys", tags=["journeys"])


@router.get("")
def list_journeys(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    approved_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = JourneysService(store).list(operator, ListJourneys(
        employee_id=employee_id, start=start, end=end, approved_only=approved_only,
        limit=limit, offset=offset))
    return {"data": [JourneyOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/mileage/{employee_id}")
def mileage(
    employee_id: str, start: str, end: str, operator: TheOperator, store: TheStore,
    already: int = Query(default=0),
) -> MileageOut:
    return MileageOut(**JourneysService(store).mileage(
        operator, employee_id, start, end, already))


@router.get("/{journey_id}")
def get_journey(journey_id: str, operator: TheOperator, store: TheStore) -> JourneyOut:
    return JourneyOut.of(JourneysService(store).get(operator, journey_id))


@router.post("", status_code=201)
def record_journey(
    dto: RecordJourney, operator: TheOperator, store: TheStore,
) -> JourneyOut:
    return JourneyOut.of(JourneysService(store).record(operator, dto))


@router.post("/{journey_id}/approve")
def approve_journey(
    journey_id: str, dto: ApproveJourney, operator: TheOperator, store: TheStore,
) -> JourneyOut:
    return JourneyOut.of(JourneysService(store).approve(operator, journey_id, dto))
