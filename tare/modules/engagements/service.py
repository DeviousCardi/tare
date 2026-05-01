"""Engagements, and whether they are caught by the rules."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Engagement, Operator
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.engagements.rules import is_inside, running, running_on, sort_by_started
from tare.modules.engagements.schemas import (
    EndEngagement, ListEngagements, OpenEngagement,
)


class EngagementsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListEngagements) -> dict:
        rows = visible_to(operator, self.store.engagements.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.running_on:
            day = a_day(query.running_on, "running_on")
            rows = [row for row in rows if running_on(row, day)]
        return page(sort_by_started(rows), query.limit, query.offset)

    def get(self, operator: Operator, engagement_id: str) -> Engagement:
        row = self.store.engagements.find(engagement_id)
        if not row:
            raise not_found("engagement", engagement_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def open(self, operator: Operator, dto: OpenEngagement) -> Engagement:
        self.employers.assert_visible(operator, dto.employer_id)
        return self.store.engagements.insert(Engagement(
            id="", employer_id=dto.employer_id, worker_name=dto.worker_name,
            intermediary=dto.intermediary, supervised=dto.supervised,
            substitution_allowed=dto.substitution_allowed,
            started_on=a_day(dto.started_on, "started_on"), ended_on=None))

    def end(
        self, operator: Operator, engagement_id: str, dto: EndEngagement,
    ) -> Engagement:
        row = self.get(operator, engagement_id)
        ended_on = a_day(dto.ended_on, "ended_on")
        if row.ended_on is not None:
            raise conflict("that engagement has already ended")
        if compare_dates(ended_on, row.started_on) < 0:
            raise refuse("an engagement cannot end before it starts")
        return self.store.engagements.update(row.id, ended_on=ended_on)

    def inside(self, operator: Operator, engagement_id: str) -> bool:
        return is_inside(self.get(operator, engagement_id))

    def running(self, operator: Operator, employer_id: str, day: str) -> list[Engagement]:
        self.employers.assert_visible(operator, employer_id)
        return running(self.store.engagements.all(), employer_id, a_day(day, "day"))
