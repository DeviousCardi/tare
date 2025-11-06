"""Routes for the contribution bands."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.bands.schemas import BandOut, ContributionOut, ListBands, PublishBand
from tare.modules.bands.service import BandsService

router = APIRouter(prefix="/bands", tags=["bands"])


@router.get("")
def list_bands(
    operator: TheOperator, store: TheStore,
    letter: str | None = Query(default=None),
    in_force_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = BandsService(store).list(operator, ListBands(
        letter=letter, in_force_on=in_force_on, limit=limit, offset=offset))
    return {"data": [BandOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{letter}/contribution")
def contribution(
    letter: str, on: str, pay: int, operator: TheOperator, store: TheStore,
) -> ContributionOut:
    return ContributionOut(**BandsService(store).contribution(letter, on, pay))


@router.get("/row/{band_id}")
def get_band(band_id: str, operator: TheOperator, store: TheStore) -> BandOut:
    return BandOut.of(BandsService(store).get(operator, band_id))


@router.post("", status_code=201)
def publish_band(dto: PublishBand, operator: TheOperator, store: TheStore) -> BandOut:
    return BandOut.of(BandsService(store).publish(operator, dto))
