"""Deduction instructions, and working them through a figure of pay."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import DeductionInstruction, Operator
from tare.modules.deductions.rules import (
    BASES, by_priority, due_in, take_from, total_short, total_taken,
)
from tare.modules.deductions.schemas import (
    InstructDeduction, ListDeductions, StopDeduction,
)
from tare.modules.elements.service import ElementsService
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.suspensions.service import SuspensionsService


class DeductionsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.elements = ElementsService(store)
        self.suspensions = SuspensionsService(store)

    def list(self, operator: Operator, query: ListDeductions) -> dict:
        rows = visible_to(operator, self.store.deductions.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.element_id:
            rows = [row for row in rows if row.element_id == query.element_id]
        if query.due_in_period is not None and query.year_starts_on:
            starts = a_day(query.year_starts_on, "year_starts_on")
            rows = [row for row in rows if due_in(row, query.due_in_period, starts)]
        return page(by_priority(rows), query.limit, query.offset)

    def get(self, operator: Operator, instruction_id: str) -> DeductionInstruction:
        row = self.store.deductions.find(instruction_id)
        if not row:
            raise not_found("deduction instruction", instruction_id)
        self.employees.get(operator, row.employee_id)
        return row

    def instruct(self, operator: Operator, dto: InstructDeduction) -> DeductionInstruction:
        person = self.employees.get(operator, dto.employee_id)
        element = self.elements.get(operator, dto.element_id)
        if element.kind != "deduction":
            raise refuse("only a deduction element can be instructed")
        if element.employer_id != person.employer_id:
            raise refuse("an instruction must name an element of the person's own employer")
        if dto.basis not in BASES:
            raise refuse(f"{dto.basis} is not a basis a deduction is quoted on")
        if dto.basis == "share" and dto.amount > 10000:
            raise refuse("a share cannot be more than the whole")
        if dto.to_period is not None and dto.to_period < dto.from_period:
            raise refuse("an instruction cannot stop before it starts")
        starts = a_day(dto.year_starts_on, "year_starts_on")
        clash = self.store.deductions.first(
            lambda row: row.employee_id == person.id
            and row.element_id == dto.element_id
            and due_in(row, dto.from_period, starts))
        if clash:
            raise conflict(
                f"{element.code} is already instructed for period {dto.from_period}")
        return self.store.deductions.insert(DeductionInstruction(
            id="", employee_id=person.id, employer_id=person.employer_id,
            element_id=dto.element_id, basis=dto.basis, amount=dto.amount,
            priority=dto.priority, from_period=dto.from_period,
            to_period=dto.to_period, year_starts_on=starts))

    def stop(
        self, operator: Operator, instruction_id: str, dto: StopDeduction,
    ) -> DeductionInstruction:
        row = self.get(operator, instruction_id)
        if row.to_period is not None:
            raise conflict("that instruction has already been stopped")
        if dto.to_period < row.from_period:
            raise refuse("an instruction cannot stop before it starts")
        return self.store.deductions.update(row.id, to_period=dto.to_period)

    def run(
        self, operator: Operator, employee_id: str, period: int, year_starts_on: str,
        pay: int,
    ) -> dict:
        self.employees.get(operator, employee_id)
        starts = a_day(year_starts_on, "year_starts_on")
        due = [row for row in self.store.deductions.all()
               if row.employee_id == employee_id and due_in(row, period, starts)]
        held = self.suspensions.held_off(operator, employee_id, period, starts)
        taken = take_from(due, pay, held)
        return {
            "employee_id": employee_id, "pay": pay,
            "lines": [{"instruction_id": row.instruction_id,
                       "element_id": row.element_id, "asked": row.asked,
                       "taken": row.taken, "short": row.short} for row in taken],
            "total_taken": total_taken(taken), "total_short": total_short(taken),
        }
