"""Rates, and what they come to."""

from __future__ import annotations

from tare.common.effective import sort_by_effective
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, PayRate
from tare.modules.contracts.rules import hourly_pay
from tare.modules.contracts.service import ContractsService
from tare.modules.elements.service import ElementsService
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.rates.rules import BASES, amount_for, for_element
from tare.modules.rates.schemas import ListRates, SetRate


class RatesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.elements = ElementsService(store)
        self.contracts = ContractsService(store)

    def list(self, operator: Operator, query: ListRates) -> dict:
        rows = visible_to(operator, self.store.rates.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.element_id:
            rows = [row for row in rows if row.element_id == query.element_id]
        if query.in_force_on:
            day = a_day(query.in_force_on, "in_force_on")
            from tare.common.effective import all_in_force_on
            rows = all_in_force_on(rows, day,
                                   lambda row: (row.employee_id, row.element_id))
        return page(sort_by_effective(rows), query.limit, query.offset)

    def get(self, operator: Operator, rate_id: str) -> PayRate:
        row = self.store.rates.find(rate_id)
        if not row:
            raise not_found("rate", rate_id)
        self.employees.get(operator, row.employee_id)
        return row

    def in_force(
        self, operator: Operator, employee_id: str, element_id: str, day: str,
    ) -> PayRate:
        self.employees.get(operator, employee_id)
        found = for_element(self.store.rates.all(), employee_id, element_id,
                            a_day(day, "day"))
        if not found:
            raise not_found("rate in force", f"{employee_id} {element_id} on {day}")
        return found

    def set(self, operator: Operator, dto: SetRate) -> PayRate:
        person = self.employees.get(operator, dto.employee_id)
        element = self.elements.get(operator, dto.element_id)
        if element.employer_id != person.employer_id:
            raise refuse("a rate must name an element of the person's own employer")
        if dto.basis not in BASES:
            raise refuse(f"{dto.basis} is not a basis a rate is quoted on")
        effective_from = a_day(dto.effective_from, "effective_from")
        clash = self.store.rates.first(
            lambda row: row.employee_id == person.id
            and row.element_id == dto.element_id
            and row.effective_from == effective_from)
        if clash:
            raise conflict(
                f"a rate for {element.code} already changes on {effective_from}")
        return self.store.rates.insert(PayRate(
            id="", employee_id=person.id, employer_id=person.employer_id,
            element_id=dto.element_id, basis=dto.basis, amount=dto.amount,
            effective_from=effective_from))

    def applied(
        self, operator: Operator, employee_id: str, element_id: str, day: str,
        hours: int,
    ) -> dict:
        if hours < 0:
            raise refuse("hours cannot be negative")
        rate = self.in_force(operator, employee_id, element_id, day)
        contract = self.contracts.in_force(operator, employee_id, day)
        return {"employee_id": employee_id, "element_id": element_id, "hours": hours,
                "amount": amount_for(rate, hours, hourly_pay(contract))}
