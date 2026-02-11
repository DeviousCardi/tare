"""Regions. Everybody reads them; only the bureau opens one."""

from __future__ import annotations

from tare.common.errors import conflict, not_found
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Region
from tare.modules.regions.rules import sort_by_code
from tare.modules.regions.schemas import ListRegions, OpenRegion


class RegionsService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def list(self, operator: Operator, query: ListRegions) -> dict:
        return page(sort_by_code(self.store.regions.all()), query.limit, query.offset)

    def get(self, operator: Operator, region_id: str) -> Region:
        row = self.store.regions.find(region_id)
        if not row:
            raise not_found("region", region_id)
        return row

    def open(self, operator: Operator, dto: OpenRegion) -> Region:
        assert_bureau(operator, "open a region")
        if self.store.regions.first(lambda row: row.code == dto.code):
            raise conflict(f"region {dto.code} already exists")
        return self.store.regions.insert(Region(id="", code=dto.code, name=dto.name))
