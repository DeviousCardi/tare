"""Awards, and what a review costs."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, PayAward
from tare.modules.awards.rules import (
    BASES, average_share, cost_of, new_salary, sort_by_employee,
)
from tare.modules.awards.schemas import ListAwards, MakeAward
from tare.modules.employees.service import EmployeesService
from tare.modules.reviews.rules import is_open
from tare.modules.reviews.service import ReviewsService


class AwardsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.reviews = ReviewsService(store)

    def list(self, operator: Operator, query: ListAwards) -> dict:
        rows = visible_to(operator, self.store.awards.all())
        if query.review_id:
            rows = [row for row in rows if row.review_id == query.review_id]
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        return page(sort_by_employee(rows), query.limit, query.offset)

    def get(self, operator: Operator, award_id: str) -> PayAward:
        row = self.store.awards.find(award_id)
        if not row:
            raise not_found("award", award_id)
        self.employees.get(operator, row.employee_id)
        return row

    def make(self, operator: Operator, dto: MakeAward) -> PayAward:
        review = self.reviews.get(operator, dto.review_id)
        person = self.employees.get(operator, dto.employee_id)
        if not is_open(review):
            raise conflict("that review has been closed")
        if person.employer_id != review.employer_id:
            raise refuse("an award must be to somebody the review covers")
        if dto.basis not in BASES:
            raise refuse(f"{dto.basis} is not a basis an award is quoted on")
        clash = self.store.awards.first(
            lambda row: row.review_id == review.id and row.employee_id == person.id)
        if clash:
            raise conflict(f"{person.reference} already has an award in that review")
        return self.store.awards.insert(PayAward(
            id="", review_id=review.id, employee_id=person.id,
            employer_id=person.employer_id, basis=dto.basis, amount=dto.amount,
            old_salary=dto.old_salary,
            new_salary=new_salary(dto.old_salary, dto.basis, dto.amount)))

    def cost(self, operator: Operator, review_id: str) -> dict:
        review = self.reviews.get(operator, review_id)
        rows = [row for row in self.store.awards.all() if row.review_id == review.id]
        return {"review_id": review.id, "awards": len(rows), "cost": cost_of(rows),
                "average_share": average_share(rows)}
