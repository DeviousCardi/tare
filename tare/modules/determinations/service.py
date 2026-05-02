"""Determinations, and what a caught engagement is deemed to pay."""

from __future__ import annotations

from tare.common.errors import conflict, not_found
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Determination, Operator
from tare.modules.determinations.rules import (
    deemed_payment, sort_by_decided, total_deemed,
)
from tare.modules.determinations.schemas import DecideEngagement, ListDeterminations
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.engagements.service import EngagementsService


class DeterminationsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.engagements = EngagementsService(store)

    def list(self, operator: Operator, query: ListDeterminations) -> dict:
        rows = visible_to(operator, self.store.determinations.all())
        if query.engagement_id:
            rows = [row for row in rows if row.engagement_id == query.engagement_id]
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.inside_only:
            rows = [row for row in rows if row.inside]
        return page(sort_by_decided(rows), query.limit, query.offset)

    def get(self, operator: Operator, determination_id: str) -> Determination:
        row = self.store.determinations.find(determination_id)
        if not row:
            raise not_found("determination", determination_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def decide(self, operator: Operator, dto: DecideEngagement) -> Determination:
        engagement = self.engagements.get(operator, dto.engagement_id)
        if self.store.determinations.first(
                lambda row: row.engagement_id == engagement.id):
            raise conflict("that engagement has already been decided")
        deemed = deemed_payment(dto.fee, dto.allowable_expenses) if dto.inside else 0
        return self.store.determinations.insert(Determination(
            id="", engagement_id=engagement.id, employer_id=engagement.employer_id,
            inside=dto.inside, fee=dto.fee,
            allowable_expenses=dto.allowable_expenses, deemed_payment=deemed,
            decided_on=a_day(dto.decided_on, "decided_on")))

    def owed(self, operator: Operator, employer_id: str) -> int:
        self.employers.assert_visible(operator, employer_id)
        return total_deemed([row for row in self.store.determinations.all()
                             if row.employer_id == employer_id])
