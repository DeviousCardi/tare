"""Absences, and the spells they make up."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Absence, Operator
from tare.modules.absences.rules import (
    KINDS, clashes_with, covers, days_between, days_of, sort_by_start, spell_of,
)
from tare.modules.absences.schemas import AmendAbsence, ListAbsences, RecordAbsence
from tare.modules.employees.rules import in_post_on
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day


class AbsencesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListAbsences) -> dict:
        rows = visible_to(operator, self.store.absences.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.kind:
            rows = [row for row in rows if row.kind == query.kind]
        if query.covering:
            day = a_day(query.covering, "covering")
            rows = [row for row in rows if covers(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, absence_id: str) -> Absence:
        row = self.store.absences.find(absence_id)
        if not row:
            raise not_found("absence", absence_id)
        self.employees.get(operator, row.employee_id)
        return row

    def record(self, operator: Operator, dto: RecordAbsence) -> Absence:
        person = self.employees.get(operator, dto.employee_id)
        if dto.kind not in KINDS:
            raise refuse(f"{dto.kind} is not a kind of absence this service holds")
        starts_on = a_day(dto.starts_on, "starts_on")
        ends_on = a_day(dto.ends_on, "ends_on")
        notified_on = a_day(dto.notified_on, "notified_on")
        if compare_dates(ends_on, starts_on) < 0:
            raise refuse("an absence cannot end before it starts")
        if not in_post_on(person, starts_on):
            raise refuse(f"{person.reference} was not in post on {starts_on}")
        fresh = Absence(id="", employee_id=person.id, employer_id=person.employer_id,
                        kind=dto.kind, starts_on=starts_on, ends_on=ends_on,
                        notified_on=notified_on)
        for row in self.store.absences.all():
            if row.employee_id == person.id and clashes_with(row, fresh):
                raise conflict(
                    f"{person.reference} is already away across {row.starts_on}")
        return self.store.absences.insert(fresh)

    def amend(self, operator: Operator, absence_id: str, dto: AmendAbsence) -> Absence:
        row = self.get(operator, absence_id)
        ends_on = a_day(dto.ends_on, "ends_on")
        if compare_dates(ends_on, row.starts_on) < 0:
            raise refuse("an absence cannot end before it starts")
        changed = Absence(id=row.id, employee_id=row.employee_id,
                          employer_id=row.employer_id, kind=row.kind,
                          starts_on=row.starts_on, ends_on=ends_on,
                          notified_on=row.notified_on)
        for other in self.store.absences.all():
            if other.id != row.id and other.employee_id == row.employee_id \
                    and clashes_with(other, changed):
                raise conflict(f"that would run into the absence from {other.starts_on}")
        return self.store.absences.update(row.id, ends_on=ends_on)

    def spell(self, operator: Operator, absence_id: str) -> dict:
        row = self.get(operator, absence_id)
        found = spell_of(self.store.absences.all(), row)
        return {"absence_id": row.id, "absences": [each.id for each in found],
                "days": sum(days_of(each) for each in found)}

    def days(self, operator: Operator, employee_id: str, start: str, end: str,
             kind: str | None = None) -> int:
        self.employees.get(operator, employee_id)
        mine = [row for row in self.store.absences.all()
                if row.employee_id == employee_id]
        return days_between(mine, a_day(start, "start"), a_day(end, "end"), kind)
