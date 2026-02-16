"""Routes for sites."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.sites.schemas import CloseSite, ListSites, OpenSite, SiteOut
from tare.modules.sites.service import SitesService

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("")
def list_sites(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    region_id: str | None = Query(default=None),
    open_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = SitesService(store).list(operator, ListSites(
        employer_id=employer_id, region_id=region_id, open_only=open_only,
        limit=limit, offset=offset))
    return {"data": [SiteOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/regions-used/{employer_id}")
def regions_used(employer_id: str, operator: TheOperator, store: TheStore) -> dict:
    return {"employer_id": employer_id,
            "regions": SitesService(store).regions_used(operator, employer_id)}


@router.get("/{site_id}")
def get_site(site_id: str, operator: TheOperator, store: TheStore) -> SiteOut:
    return SiteOut.of(SitesService(store).get(operator, site_id))


@router.post("", status_code=201)
def open_site(dto: OpenSite, operator: TheOperator, store: TheStore) -> SiteOut:
    return SiteOut.of(SitesService(store).open(operator, dto))


@router.post("/{site_id}/close")
def close_site(
    site_id: str, dto: CloseSite, operator: TheOperator, store: TheStore,
) -> SiteOut:
    return SiteOut.of(SitesService(store).close(operator, site_id, dto))
