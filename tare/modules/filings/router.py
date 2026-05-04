"""Routes for filings."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.filings.schemas import (
    FilingOut, FilingStateOut, ListFilings, RaiseFiling,
)
from tare.modules.filings.service import FilingsService

router = APIRouter(prefix="/filings", tags=["filings"])


@router.get("")
def list_filings(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    period: int | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = FilingsService(store).list(operator, ListFilings(
        employer_id=employer_id, period=period, limit=limit, offset=offset))
    return {"data": [FilingOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{filing_id}")
def get_filing(filing_id: str, operator: TheOperator, store: TheStore) -> FilingOut:
    return FilingOut.of(FilingsService(store).get(operator, filing_id))


@router.get("/{filing_id}/state")
def filing_state(
    filing_id: str, on: str, operator: TheOperator, store: TheStore,
) -> FilingStateOut:
    return FilingStateOut(**FilingsService(store).state(operator, filing_id, on))


@router.post("", status_code=201)
def raise_filing(dto: RaiseFiling, operator: TheOperator, store: TheStore) -> FilingOut:
    return FilingOut.of(FilingsService(store).raise_it(operator, dto))
