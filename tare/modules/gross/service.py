"""Working out what somebody earned in a period."""

from __future__ import annotations

from tare.common.errors import not_found, refuse
from tare.common.store import Store
from tare.common.types import Operator
from tare.modules.calendars.rules import period_window
from tare.modules.calendars.service import CalendarsService
from tare.modules.contracts.rules import hourly_pay
from tare.modules.contracts.service import ContractsService
from tare.modules.elements.rules import (
    contributory_total, gross_total, pensionable_total, taxable_total,
)
from tare.modules.elements.service import ElementsService
from tare.modules.employees.rules import in_post_on
from tare.modules.employees.service import EmployeesService
from tare.modules.gross.rules import Piece, combine, entries_for
from tare.modules.rates.rules import for_element, is_hours_based
from tare.modules.timesheets.rules import hours_by_element


class GrossService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.contracts = ContractsService(store)
        self.elements = ElementsService(store)
        self.calendars = CalendarsService(store)

    def of(self, operator: Operator, employee_id: str, calendar_id: str,
           period: int) -> dict:
        """What one person earned in one period of one calendar."""
        person = self.employees.get(operator, employee_id)
        calendar = self.calendars.get(operator, calendar_id)
        if calendar.employer_id != person.employer_id:
            raise refuse("that calendar belongs to another employer")
        window = period_window(calendar, period)
        if not in_post_on(person, window.end) and not in_post_on(person, window.start):
            raise refuse(f"{person.reference} was not in post across that period")

        contract = self.contracts.in_force(operator, person.id, window.end)
        per_hour = hourly_pay(contract)
        rates = [row for row in self.store.rates.all() if row.employee_id == person.id]
        hours = hours_by_element(
            [row for row in self.store.timesheets.all()
             if row.employee_id == person.id], window.start, window.end)

        pieces: list[Piece] = []
        for element_id, worked in hours.items():
            rate = for_element(rates, person.id, element_id, window.end)
            if rate and is_hours_based(rate):
                pieces.append(Piece(element_id=element_id, hours=worked, rate=rate))
        for rate in rates:
            found = for_element(rates, person.id, rate.element_id, window.end)
            if found and not is_hours_based(found) and found.id == rate.id:
                pieces.append(Piece(element_id=rate.element_id, hours=0, rate=found))

        entries = combine(entries_for(pieces, per_hour))
        elements = [row for row in self.store.elements.all()
                    if row.employer_id == person.employer_id]
        by_id = {row.id: row for row in elements}
        worked_hours = {piece.element_id: piece.hours for piece in pieces}
        lines = [{"element_id": entry.element_id,
                  "code": by_id[entry.element_id].code,
                  "name": by_id[entry.element_id].name,
                  "hours": worked_hours.get(entry.element_id, 0),
                  "amount": entry.amount}
                 for entry in entries if entry.element_id in by_id]
        return {
            "employee_id": person.id, "calendar_id": calendar.id, "period": period,
            "start": window.start, "end": window.end, "lines": lines,
            "gross": gross_total(entries, elements),
            "taxable": taxable_total(entries, elements),
            "contributory": contributory_total(entries, elements),
            "pensionable": pensionable_total(entries, elements),
        }
