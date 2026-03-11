"""Pension schemes, and what a figure of pensionable pay puts in."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, PensionScheme
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.pensions.rules import (
    employee_share, employer_share, is_open_on, qualifies, sort_by_code, total_share,
)
from tare.modules.pensions.schemas import CloseScheme, ListSchemes, OpenScheme
from tare.modules.providers.service import ProvidersService


class PensionsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.providers = ProvidersService(store)

    def list(self, operator: Operator, query: ListSchemes) -> dict:
        rows = visible_to(operator, self.store.schemes.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.open_on:
            day = a_day(query.open_on, "open_on")
            rows = [row for row in rows if is_open_on(row, day)]
        return page(sort_by_code(rows), query.limit, query.offset)

    def get(self, operator: Operator, scheme_id: str) -> PensionScheme:
        row = self.store.schemes.find(scheme_id)
        if not row:
            raise not_found("scheme", scheme_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def open(self, operator: Operator, dto: OpenScheme) -> PensionScheme:
        self.employers.assert_visible(operator, dto.employer_id)
        provider = self.providers.get(operator, dto.provider_id)
        if provider.kind != "pension":
            raise refuse("a scheme must be held with a pension provider")
        if self.store.schemes.first(
                lambda row: row.employer_id == dto.employer_id and row.code == dto.code):
            raise conflict(f"scheme {dto.code} already exists")
        return self.store.schemes.insert(PensionScheme(
            id="", employer_id=dto.employer_id, provider_id=dto.provider_id,
            code=dto.code, name=dto.name,
            employee_basis_points=dto.employee_basis_points,
            employer_basis_points=dto.employer_basis_points,
            qualifying_floor=dto.qualifying_floor,
            opened_on=a_day(dto.opened_on, "opened_on"), closed_on=None))

    def close(
        self, operator: Operator, scheme_id: str, dto: CloseScheme,
    ) -> PensionScheme:
        row = self.get(operator, scheme_id)
        closed_on = a_day(dto.closed_on, "closed_on")
        if row.closed_on is not None:
            raise conflict("that scheme is already closed")
        if compare_dates(closed_on, row.opened_on) < 0:
            raise refuse("a scheme cannot close before it opened")
        return self.store.schemes.update(row.id, closed_on=closed_on)

    def shares(self, operator: Operator, scheme_id: str, pensionable: int) -> dict:
        row = self.get(operator, scheme_id)
        if pensionable < 0:
            raise refuse("pensionable pay cannot be negative")
        return {"scheme_id": row.id, "pensionable": pensionable,
                "qualifies": qualifies(row, pensionable),
                "employee": employee_share(row, pensionable),
                "employer": employer_share(row, pensionable),
                "total": total_share(row, pensionable)}
