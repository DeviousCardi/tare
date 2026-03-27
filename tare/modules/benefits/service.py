"""Benefit awards, and what they add to somebody's pay."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import BenefitAward, Operator
from tare.modules.benefits.rules import held_by, held_on, sort_by_start, taxable_value
from tare.modules.benefits.schemas import AwardBenefit, EndBenefit, ListBenefits
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.valuations.rules import for_days
from tare.modules.valuations.service import ValuationsService


class BenefitsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.valuations = ValuationsService(store)

    def list(self, operator: Operator, query: ListBenefits) -> dict:
        rows = visible_to(operator, self.store.benefits.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.class_id:
            rows = [row for row in rows if row.class_id == query.class_id]
        if query.held_on:
            day = a_day(query.held_on, "held_on")
            rows = [row for row in rows if held_on(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, award_id: str) -> BenefitAward:
        row = self.store.benefits.find(award_id)
        if not row:
            raise not_found("benefit", award_id)
        self.employees.get(operator, row.employee_id)
        return row

    def award(self, operator: Operator, dto: AwardBenefit) -> BenefitAward:
        person = self.employees.get(operator, dto.employee_id)
        kind = self.valuations.get(operator, dto.class_id)
        if kind.employer_id != person.employer_id:
            raise refuse("a benefit must be one the person's own employer provides")
        starts_on = a_day(dto.starts_on, "starts_on")
        ends_on = a_day(dto.ends_on, "ends_on") if dto.ends_on else None
        if ends_on and compare_dates(ends_on, starts_on) < 0:
            raise refuse("a benefit cannot end before it starts")
        standing = [row for row in held_by(self.store.benefits.all(), person.id, starts_on)
                    if row.class_id == dto.class_id]
        if standing:
            raise conflict(f"{person.reference} already has {kind.code} on {starts_on}")
        return self.store.benefits.insert(BenefitAward(
            id="", employee_id=person.id, employer_id=person.employer_id,
            class_id=dto.class_id, contribution=dto.contribution,
            starts_on=starts_on, ends_on=ends_on))

    def end(self, operator: Operator, award_id: str, dto: EndBenefit) -> BenefitAward:
        row = self.get(operator, award_id)
        ends_on = a_day(dto.ends_on, "ends_on")
        if row.ends_on is not None:
            raise conflict("that benefit has already ended")
        if compare_dates(ends_on, row.starts_on) < 0:
            raise refuse("a benefit cannot end before it starts")
        return self.store.benefits.update(row.id, ends_on=ends_on)

    def value(self, operator: Operator, award_id: str, days: int) -> dict:
        row = self.get(operator, award_id)
        kind = self.valuations.get(operator, row.class_id)
        worth = for_days(kind, days)
        return {"award_id": row.id, "days": days, "worth": worth,
                "contribution": row.contribution,
                "taxable": taxable_value(row, worth)}
