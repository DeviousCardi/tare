"""Expense claims, and what is owed back."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import ExpenseClaim, Operator
from tare.modules.elements.service import ElementsService
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.expenses.rules import (
    CLAIMED, STATUSES, between, by_kind, comes_to, is_open, sort_by_incurred,
)
from tare.modules.expenses.schemas import DecideClaim, ListClaims, MakeClaim


class ExpensesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.elements = ElementsService(store)

    def list(self, operator: Operator, query: ListClaims) -> dict:
        rows = visible_to(operator, self.store.expenses.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.status:
            rows = [row for row in rows if row.status == query.status]
        if query.start and query.end:
            rows = between(rows, a_day(query.start, "start"), a_day(query.end, "end"))
        return page(sort_by_incurred(rows), query.limit, query.offset)

    def get(self, operator: Operator, claim_id: str) -> ExpenseClaim:
        row = self.store.expenses.find(claim_id)
        if not row:
            raise not_found("claim", claim_id)
        self.employees.get(operator, row.employee_id)
        return row

    def make(self, operator: Operator, dto: MakeClaim) -> ExpenseClaim:
        person = self.employees.get(operator, dto.employee_id)
        element = self.elements.get(operator, dto.element_id)
        if element.kind != "payment":
            raise refuse("a claim must be paid as a payment element")
        incurred_on = a_day(dto.incurred_on, "incurred_on")
        claimed_on = a_day(dto.claimed_on, "claimed_on")
        if compare_dates(claimed_on, incurred_on) < 0:
            raise refuse("a claim cannot be made before the cost was incurred")
        return self.store.expenses.insert(ExpenseClaim(
            id="", employee_id=person.id, employer_id=person.employer_id,
            element_id=dto.element_id, kind=dto.kind, amount=dto.amount,
            incurred_on=incurred_on, claimed_on=claimed_on, status=CLAIMED))

    def decide(self, operator: Operator, claim_id: str, dto: DecideClaim) -> ExpenseClaim:
        row = self.get(operator, claim_id)
        if dto.status not in STATUSES:
            raise refuse(f"{dto.status} is not something a claim can become")
        if dto.status == CLAIMED:
            raise refuse("a claim cannot be put back to being made")
        if not is_open(row):
            raise conflict(f"that claim was already {row.status}")
        return self.store.expenses.update(row.id, status=dto.status)

    def owed(self, operator: Operator, employee_id: str) -> dict:
        self.employees.get(operator, employee_id)
        mine = [row for row in self.store.expenses.all()
                if row.employee_id == employee_id]
        return {"employee_id": employee_id, "comes_to": comes_to(mine),
                "by_kind": by_kind(mine)}
