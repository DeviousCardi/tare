"""Carried balances, and clearing them."""

from __future__ import annotations

from tare.common.errors import conflict, not_found
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import CarriedBalance, Operator
from tare.modules.balances.rules import (
    is_open, open_balances, outstanding, sort_by_period, to_carry,
)
from tare.modules.balances.schemas import ClearBalance, HoldOver, ListBalances
from tare.modules.elements.service import ElementsService
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day


class BalancesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.elements = ElementsService(store)

    def list(self, operator: Operator, query: ListBalances) -> dict:
        rows = visible_to(operator, self.store.balances.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.element_id:
            rows = [row for row in rows if row.element_id == query.element_id]
        if query.open_only:
            rows = [row for row in rows if is_open(row)]
        return page(sort_by_period(rows), query.limit, query.offset)

    def get(self, operator: Operator, balance_id: str) -> CarriedBalance:
        row = self.store.balances.find(balance_id)
        if not row:
            raise not_found("balance", balance_id)
        self.employees.get(operator, row.employee_id)
        return row

    def hold_over(self, operator: Operator, dto: HoldOver) -> CarriedBalance:
        person = self.employees.get(operator, dto.employee_id)
        self.elements.get(operator, dto.element_id)
        starts = a_day(dto.year_starts_on, "year_starts_on")
        clash = self.store.balances.first(
            lambda row: row.employee_id == person.id
            and row.element_id == dto.element_id
            and row.year_starts_on == starts and row.period == dto.period)
        if clash:
            raise conflict(
                f"{person.reference} already has a balance held from period {dto.period}")
        return self.store.balances.insert(CarriedBalance(
            id="", employee_id=person.id, employer_id=person.employer_id,
            element_id=dto.element_id, year_starts_on=starts, period=dto.period,
            shortfall=dto.shortfall, carried=to_carry(dto.shortfall),
            cleared_on=None))

    def clear(
        self, operator: Operator, balance_id: str, dto: ClearBalance,
    ) -> CarriedBalance:
        row = self.get(operator, balance_id)
        if not is_open(row):
            raise conflict("that balance has already been cleared")
        return self.store.balances.update(
            row.id, cleared_on=a_day(dto.cleared_on, "cleared_on"))

    def outstanding(self, operator: Operator, employee_id: str, element_id: str) -> int:
        self.employees.get(operator, employee_id)
        return outstanding(self.store.balances.all(), employee_id, element_id)

    def open_for(self, operator: Operator, employee_id: str) -> list[CarriedBalance]:
        self.employees.get(operator, employee_id)
        return open_balances(self.store.balances.all(), employee_id)
