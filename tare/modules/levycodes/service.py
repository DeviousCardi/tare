"""Levy codes. Everybody reads them; only the bureau publishes one."""

from __future__ import annotations

from tare.common.effective import sort_by_effective
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import LevyCode, Operator
from tare.modules.employers.schemas import a_day
from tare.modules.levycodes.rules import (
    BASES, PERIODS_A_YEAR, every_code_on, for_code, free_pay_for_period,
)
from tare.modules.levycodes.schemas import ListLevyCodes, PublishLevyCode


class LevyCodesService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def list(self, operator: Operator, query: ListLevyCodes) -> dict:
        rows = sort_by_effective(self.store.levy_codes.all())
        if query.code:
            rows = [row for row in rows if row.code == query.code]
        if query.in_force_on:
            rows = every_code_on(rows, a_day(query.in_force_on, "in_force_on"))
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, levy_code_id: str) -> LevyCode:
        row = self.store.levy_codes.find(levy_code_id)
        if not row:
            raise not_found("levy code", levy_code_id)
        return row

    def in_force(self, code: str, day: str) -> LevyCode:
        """The version of a code governing a day, or a refusal saying none is."""
        found = for_code(self.store.levy_codes.all(), code, a_day(day, "day"))
        if not found:
            raise not_found("levy code in force", f"{code} on {day}")
        return found

    def publish(self, operator: Operator, dto: PublishLevyCode) -> LevyCode:
        assert_bureau(operator, "publish a levy code")
        effective_from = a_day(dto.effective_from, "effective_from")
        if dto.basis not in BASES:
            raise refuse(f"{dto.basis} is not a basis a levy code is worked out on")
        clash = self.store.levy_codes.first(
            lambda row: row.code == dto.code and row.effective_from == effective_from)
        if clash:
            raise conflict(f"levy code {dto.code} already changes on {effective_from}")
        return self.store.levy_codes.insert(LevyCode(
            id="", code=dto.code, description=dto.description,
            annual_allowance=dto.annual_allowance, basis=dto.basis,
            effective_from=effective_from))

    def free_pay(self, code: str, day: str, frequency: str, period: int) -> dict:
        if frequency not in PERIODS_A_YEAR:
            raise refuse(f"{frequency} is not a frequency this service runs")
        row = self.in_force(code, day)
        return {"code": code, "frequency": frequency, "period": period,
                "free_pay": free_pay_for_period(row, frequency, period)}
