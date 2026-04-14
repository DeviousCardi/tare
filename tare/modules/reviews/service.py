"""Reviews, and who they cover."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Employee, Operator, PayReview
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.reviews.rules import is_open, population_of, sort_by_effective
from tare.modules.reviews.schemas import CloseReview, ListReviews, OpenReview


class ReviewsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListReviews) -> dict:
        rows = visible_to(operator, self.store.reviews.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.open_only:
            rows = [row for row in rows if is_open(row)]
        return page(sort_by_effective(rows), query.limit, query.offset)

    def get(self, operator: Operator, review_id: str) -> PayReview:
        row = self.store.reviews.find(review_id)
        if not row:
            raise not_found("review", review_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def open(self, operator: Operator, dto: OpenReview) -> PayReview:
        self.employers.assert_visible(operator, dto.employer_id)
        if self.store.reviews.first(lambda row: row.reference == dto.reference):
            raise conflict(f"review {dto.reference} has already been opened")
        return self.store.reviews.insert(PayReview(
            id="", employer_id=dto.employer_id, reference=dto.reference,
            effective_from=a_day(dto.effective_from, "effective_from"),
            opened_on=a_day(dto.opened_on, "opened_on"), closed_on=None))

    def close(self, operator: Operator, review_id: str, dto: CloseReview) -> PayReview:
        row = self.get(operator, review_id)
        closed_on = a_day(dto.closed_on, "closed_on")
        if not is_open(row):
            raise conflict("that review has already been closed")
        if compare_dates(closed_on, row.opened_on) < 0:
            raise refuse("a review cannot close before it was opened")
        return self.store.reviews.update(row.id, closed_on=closed_on)

    def population(self, operator: Operator, review_id: str) -> list[Employee]:
        row = self.get(operator, review_id)
        return population_of(row, self.store.employees.all())
