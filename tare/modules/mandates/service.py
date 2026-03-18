"""Mandates, and where somebody's pay is sent."""

from __future__ import annotations

from tare.common.dates import add_days, compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Mandate, Operator
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.mandates.rules import sort_by_start, standing_for, stands_on
from tare.modules.mandates.schemas import EndMandate, ListMandates, SetMandate
from tare.modules.providers.rules import account_is_sound


class MandatesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListMandates) -> dict:
        rows = visible_to(operator, self.store.mandates.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.standing_on:
            day = a_day(query.standing_on, "standing_on")
            rows = [row for row in rows if stands_on(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, mandate_id: str) -> Mandate:
        row = self.store.mandates.find(mandate_id)
        if not row:
            raise not_found("mandate", mandate_id)
        self.employees.get(operator, row.employee_id)
        return row

    def standing(self, operator: Operator, employee_id: str, day: str) -> Mandate:
        self.employees.get(operator, employee_id)
        found = standing_for(self.store.mandates.all(), employee_id, a_day(day, "day"))
        if not found:
            raise not_found("mandate standing", f"{employee_id} on {day}")
        return found

    def set(self, operator: Operator, dto: SetMandate) -> Mandate:
        """Point somebody's pay somewhere new, ending what stood before."""
        person = self.employees.get(operator, dto.employee_id)
        if not account_is_sound(dto.account):
            raise refuse(f"{dto.account} does not read as an account")
        starts_on = a_day(dto.starts_on, "starts_on")
        standing = standing_for(self.store.mandates.all(), person.id, starts_on)
        if standing:
            if standing.starts_on == starts_on:
                raise conflict(f"a mandate already starts on {starts_on}")
            self.store.mandates.update(standing.id, ends_on=add_days(starts_on, -1))
        return self.store.mandates.insert(Mandate(
            id="", employee_id=person.id, employer_id=person.employer_id,
            account=dto.account, holder=dto.holder, starts_on=starts_on,
            ends_on=None))

    def end(self, operator: Operator, mandate_id: str, dto: EndMandate) -> Mandate:
        row = self.get(operator, mandate_id)
        ends_on = a_day(dto.ends_on, "ends_on")
        if row.ends_on is not None:
            raise conflict("that mandate has already ended")
        if compare_dates(ends_on, row.starts_on) < 0:
            raise refuse("a mandate cannot end before it starts")
        return self.store.mandates.update(row.id, ends_on=ends_on)
