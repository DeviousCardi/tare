"""Sites, and which region each one sits in."""

from __future__ import annotations

from tare.common.errors import conflict, not_found
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Site
from tare.modules.employers.service import EmployersService
from tare.modules.regions.service import RegionsService
from tare.modules.sites.rules import in_region, open_sites, regions_used, sort_by_code
from tare.modules.sites.schemas import CloseSite, ListSites, OpenSite


class SitesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.regions = RegionsService(store)

    def list(self, operator: Operator, query: ListSites) -> dict:
        rows = visible_to(operator, self.store.sites.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.region_id:
            rows = in_region(rows, query.region_id)
        if query.open_only:
            rows = open_sites(rows)
        return page(sort_by_code(rows), query.limit, query.offset)

    def get(self, operator: Operator, site_id: str) -> Site:
        row = self.store.sites.find(site_id)
        if not row:
            raise not_found("site", site_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def open(self, operator: Operator, dto: OpenSite) -> Site:
        self.employers.assert_visible(operator, dto.employer_id)
        self.regions.get(operator, dto.region_id)
        if self.store.sites.first(
                lambda row: row.employer_id == dto.employer_id and row.code == dto.code):
            raise conflict(f"site {dto.code} already exists")
        return self.store.sites.insert(Site(
            id="", employer_id=dto.employer_id, region_id=dto.region_id,
            code=dto.code, name=dto.name, closed=False))

    def close(self, operator: Operator, site_id: str, dto: CloseSite) -> Site:
        row = self.get(operator, site_id)
        if row.closed and dto.closed:
            raise conflict(f"site {row.code} is already closed")
        return self.store.sites.update(row.id, closed=dto.closed)

    def regions_used(self, operator: Operator, employer_id: str) -> list[str]:
        self.employers.assert_visible(operator, employer_id)
        return regions_used([row for row in self.store.sites.all()
                             if row.employer_id == employer_id])
