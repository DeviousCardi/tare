"""Contribution bands. Everybody reads them; only the bureau publishes."""

from __future__ import annotations

from tare.common.effective import sort_by_effective
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Band, Operator
from tare.modules.bands.rules import bands_for, contribution_on, sort_by_floor
from tare.modules.bands.schemas import ListBands, PublishBand
from tare.modules.employers.schemas import a_day


class BandsService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def list(self, operator: Operator, query: ListBands) -> dict:
        rows = sort_by_effective(self.store.bands.all())
        if query.letter and query.in_force_on:
            rows = bands_for(rows, query.letter, a_day(query.in_force_on, "in_force_on"))
        elif query.letter:
            rows = sort_by_floor([row for row in rows if row.letter == query.letter])
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, band_id: str) -> Band:
        row = self.store.bands.find(band_id)
        if not row:
            raise not_found("band", band_id)
        return row

    def in_force(self, letter: str, day: str) -> list[Band]:
        found = bands_for(self.store.bands.all(), letter, a_day(day, "day"))
        if not found:
            raise not_found("bands in force", f"{letter} on {day}")
        return found

    def publish(self, operator: Operator, dto: PublishBand) -> Band:
        assert_bureau(operator, "publish a band")
        effective_from = a_day(dto.effective_from, "effective_from")
        if dto.to_pay is not None and dto.to_pay < dto.from_pay:
            raise refuse("a band cannot end below where it starts")
        clash = self.store.bands.first(
            lambda row: row.letter == dto.letter
            and row.effective_from == effective_from
            and row.from_pay == dto.from_pay)
        if clash:
            raise conflict(
                f"band {dto.letter} already starts at {dto.from_pay} on {effective_from}")
        return self.store.bands.insert(Band(
            id="", letter=dto.letter, from_pay=dto.from_pay, to_pay=dto.to_pay,
            rate_basis_points=dto.rate_basis_points, effective_from=effective_from))

    def contribution(self, letter: str, day: str, pay: int) -> dict:
        if pay < 0:
            raise refuse("pay cannot be negative")
        return {"letter": letter, "pay": pay,
                "contribution": contribution_on(pay, self.in_force(letter, day))}
