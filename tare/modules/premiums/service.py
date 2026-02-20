"""Premiums, and what they come to."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Premium
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.premiums.rules import best_of, covers_hour, premium_on, sort_by_code
from tare.modules.premiums.schemas import DefinePremium, ListPremiums


class PremiumsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListPremiums) -> dict:
        rows = visible_to(operator, self.store.premiums.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.covering_hour is not None:
            rows = [row for row in rows if covers_hour(row, query.covering_hour)]
        return page(sort_by_code(rows), query.limit, query.offset)

    def get(self, operator: Operator, premium_id: str) -> Premium:
        row = self.store.premiums.find(premium_id)
        if not row:
            raise not_found("premium", premium_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def define(self, operator: Operator, dto: DefinePremium) -> Premium:
        self.employers.assert_visible(operator, dto.employer_id)
        if dto.from_hour == dto.to_hour:
            raise refuse("a premium that starts and ends on the hour covers nothing")
        if self.store.premiums.first(
                lambda row: row.employer_id == dto.employer_id and row.code == dto.code):
            raise conflict(f"premium {dto.code} already exists")
        return self.store.premiums.insert(Premium(
            id="", employer_id=dto.employer_id, code=dto.code, name=dto.name,
            rate_basis_points=dto.rate_basis_points, from_hour=dto.from_hour,
            to_hour=dto.to_hour, weekend_only=dto.weekend_only))

    def best_for(self, operator: Operator, employer_id: str, hour: int, day: str) -> Premium:
        self.employers.assert_visible(operator, employer_id)
        mine = [row for row in self.store.premiums.all()
                if row.employer_id == employer_id]
        found = best_of(mine, hour, a_day(day, "day"))
        if not found:
            raise not_found("premium covering", f"hour {hour} on {day}")
        return found

    def uplift(self, operator: Operator, premium_id: str, hourly_pay: int,
               hours: int) -> dict:
        row = self.get(operator, premium_id)
        if hours < 0 or hourly_pay < 0:
            raise refuse("hours and pay cannot be negative")
        return {"premium_id": row.id, "hourly_pay": hourly_pay, "hours": hours,
                "uplift": premium_on(row, hourly_pay, hours)}
