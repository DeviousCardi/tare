"""Loan plans, and what they take out of a period's pay."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import LoanPlan, Operator
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.loanplans.rules import (
    PLAN_TYPES, above_threshold, due_now, live_plans, remaining, settled,
    sort_by_started,
)
from tare.modules.loanplans.schemas import (
    CollectOnPlan, ListPlans, SettlePlan, StartPlan,
)


class LoanPlansService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListPlans) -> dict:
        rows = visible_to(operator, self.store.loan_plans.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.live_only:
            rows = [row for row in rows if not settled(row)]
        return page(sort_by_started(rows), query.limit, query.offset)

    def get(self, operator: Operator, plan_id: str) -> LoanPlan:
        row = self.store.loan_plans.find(plan_id)
        if not row:
            raise not_found("loan plan", plan_id)
        self.employees.get(operator, row.employee_id)
        return row

    def start(self, operator: Operator, dto: StartPlan) -> LoanPlan:
        person = self.employees.get(operator, dto.employee_id)
        if dto.plan_type not in PLAN_TYPES:
            raise refuse(f"{dto.plan_type} is not a plan the Revenue publishes")
        if self.store.loan_plans.first(lambda row: row.reference == dto.reference):
            raise conflict(f"plan {dto.reference} has already been started")
        return self.store.loan_plans.insert(LoanPlan(
            id="", employee_id=person.id, employer_id=person.employer_id,
            reference=dto.reference, plan_type=dto.plan_type, total=dto.total,
            collected=0, period_threshold=dto.period_threshold,
            rate_basis_points=dto.rate_basis_points,
            started_on=a_day(dto.started_on, "started_on"), settled_on=None))

    def collect(self, operator: Operator, plan_id: str, dto: CollectOnPlan) -> LoanPlan:
        row = self.get(operator, plan_id)
        if settled(row):
            raise conflict("that plan is already settled")
        if dto.amount > remaining(row):
            raise refuse("a plan cannot collect more than it is still owed")
        return self.store.loan_plans.update(row.id, collected=row.collected + dto.amount)

    def settle(self, operator: Operator, plan_id: str, dto: SettlePlan) -> LoanPlan:
        row = self.get(operator, plan_id)
        settled_on = a_day(dto.settled_on, "settled_on")
        if row.settled_on is not None:
            raise conflict("that plan has already been settled")
        if compare_dates(settled_on, row.started_on) < 0:
            raise refuse("a plan cannot settle before it started")
        return self.store.loan_plans.update(row.id, settled_on=settled_on)

    def due(self, operator: Operator, plan_id: str, pay: int) -> dict:
        row = self.get(operator, plan_id)
        if pay < 0:
            raise refuse("pay cannot be negative")
        return {"plan_id": row.id, "pay": pay,
                "above_threshold": above_threshold(row, pay),
                "due": due_now(row, pay), "remaining": remaining(row)}

    def live_for(self, operator: Operator, employee_id: str) -> list[LoanPlan]:
        self.employees.get(operator, employee_id)
        return live_plans(self.store.loan_plans.all(), employee_id)
