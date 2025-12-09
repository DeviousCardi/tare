"""Pay elements, and what a run of entries against them comes to."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, PayElement
from tare.modules.elements.rules import (
    KINDS, Entry, contributory_total, deduction_total, gross_total, pensionable_total,
    sort_by_code, taxable_total,
)
from tare.modules.elements.schemas import ChangeElement, DefineElement, ListElements
from tare.modules.employers.service import EmployersService


class ElementsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListElements) -> dict:
        rows = visible_to(operator, self.store.elements.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.kind:
            rows = [row for row in rows if row.kind == query.kind]
        return page(sort_by_code(rows), query.limit, query.offset)

    def get(self, operator: Operator, element_id: str) -> PayElement:
        row = self.store.elements.find(element_id)
        if not row:
            raise not_found("element", element_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def define(self, operator: Operator, dto: DefineElement) -> PayElement:
        self.employers.assert_visible(operator, dto.employer_id)
        if dto.kind not in KINDS:
            raise refuse(f"{dto.kind} is not something an element can be")
        if self.store.elements.first(
                lambda row: row.employer_id == dto.employer_id and row.code == dto.code):
            raise conflict(f"element {dto.code} already exists")
        if dto.kind == "deduction" and dto.pensionable:
            raise refuse("a deduction cannot be pensionable")
        return self.store.elements.insert(PayElement(
            id="", employer_id=dto.employer_id, code=dto.code, name=dto.name,
            kind=dto.kind, taxable=dto.taxable, contributory=dto.contributory,
            pensionable=dto.pensionable))

    def change(
        self, operator: Operator, element_id: str, dto: ChangeElement,
    ) -> PayElement:
        row = self.get(operator, element_id)
        changes = {name: value for name, value in dto.model_dump().items()
                   if value is not None}
        if changes.get("pensionable") and row.kind == "deduction":
            raise refuse("a deduction cannot be pensionable")
        if not changes:
            raise refuse("nothing was asked to change")
        return self.store.elements.update(row.id, **changes)

    def totals(self, operator: Operator, employer_id: str, entries: list[Entry]) -> dict:
        self.employers.assert_visible(operator, employer_id)
        elements = [row for row in self.store.elements.all()
                    if row.employer_id == employer_id]
        known = {row.id for row in elements}
        for entry in entries:
            if entry.element_id not in known:
                raise not_found("element", entry.element_id)
        return {
            "gross": gross_total(entries, elements),
            "deductions": deduction_total(entries, elements),
            "taxable": taxable_total(entries, elements),
            "contributory": contributory_total(entries, elements),
            "pensionable": pensionable_total(entries, elements),
        }
