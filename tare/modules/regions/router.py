"""Routes for regions."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.regions.schemas import ListRegions, OpenRegion, RegionOut
from tare.modules.regions.service import RegionsService

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("")
def list_regions(
    operator: TheOperator, store: TheStore,
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = RegionsService(store).list(operator, ListRegions(limit=limit, offset=offset))
    return {"data": [RegionOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{region_id}")
def get_region(region_id: str, operator: TheOperator, store: TheStore) -> RegionOut:
    return RegionOut.of(RegionsService(store).get(operator, region_id))


@router.post("", status_code=201)
def open_region(dto: OpenRegion, operator: TheOperator, store: TheStore) -> RegionOut:
    return RegionOut.of(RegionsService(store).open(operator, dto))
