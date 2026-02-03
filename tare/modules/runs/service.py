"""Payroll runs, and committing one."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import DomainError, conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Payslip, PayrollRun, PayslipLine
from tare.modules.calendars.service import CalendarsService
from tare.modules.employees.rules import in_post_on
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.net.service import NetService
from tare.modules.runs.rules import (
    COMMITTED, DRAFT, gross_total, headcount, is_open, revenue_total, run_total,
    sort_by_period,
)
from tare.modules.runs.schemas import CommitRun, ListRuns, OpenRun


class RunsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.calendars = CalendarsService(store)
        self.net = NetService(store)

    def list(self, operator: Operator, query: ListRuns) -> dict:
        rows = visible_to(operator, self.store.runs.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.calendar_id:
            rows = [row for row in rows if row.calendar_id == query.calendar_id]
        if query.period is not None:
            rows = [row for row in rows if row.period == query.period]
        if query.status:
            rows = [row for row in rows if row.status == query.status]
        return page(sort_by_period(rows), query.limit, query.offset)

    def get(self, operator: Operator, run_id: str) -> PayrollRun:
        row = self.store.runs.find(run_id)
        if not row:
            raise not_found("run", run_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def open(self, operator: Operator, dto: OpenRun) -> PayrollRun:
        self.employers.assert_visible(operator, dto.employer_id)
        calendar = self.calendars.get(operator, dto.calendar_id)
        if calendar.employer_id != dto.employer_id:
            raise refuse("that calendar belongs to another employer")
        if dto.period > calendar.periods:
            raise refuse(f"period {dto.period} is not in a year of {calendar.periods}")
        opened_on = a_day(dto.opened_on, "opened_on")
        clash = self.store.runs.first(
            lambda row: row.calendar_id == dto.calendar_id
            and row.period == dto.period and row.status != "abandoned")
        if clash:
            raise conflict(f"period {dto.period} has already been run")
        return self.store.runs.insert(PayrollRun(
            id="", employer_id=dto.employer_id, calendar_id=dto.calendar_id,
            period=dto.period, status=DRAFT, opened_on=opened_on,
            committed_on=None))

    def commit(self, operator: Operator, run_id: str, dto: CommitRun) -> PayrollRun:
        """Work out every payslip the run covers and write it down for good."""
        row = self.get(operator, run_id)
        if not is_open(row):
            raise conflict(f"that run was already {row.status}")
        committed_on = a_day(dto.committed_on, "committed_on")
        if compare_dates(committed_on, row.opened_on) < 0:
            raise refuse("a run cannot commit before it was opened")

        window = self.calendars.period(operator, row.calendar_id, row.period)
        for person in self.store.employees.all():
            if person.employer_id != row.employer_id:
                continue
            if not in_post_on(person, window["end"]) and \
                    not in_post_on(person, window["start"]):
                continue
            try:
                worked = self.net.of(operator, person.id, row.calendar_id, row.period)
            except DomainError:
                # Somebody with no contract or no rate across the period has
                # nothing to be paid. A run passes over them rather than
                # stopping: one unfinished record must not hold up the payroll
                # for everybody else, and the missing payslip is what shows it.
                continue
            slip = self.store.payslips.insert(Payslip(
                id="", run_id=row.id, employee_id=person.id,
                employer_id=person.employer_id, period=row.period,
                start=worked["start"], end=worked["end"], gross=worked["gross"],
                taxable=worked["taxable"], free_pay=worked["free_pay"],
                levy=worked["levy"], contributory=worked["contributory"],
                contributions=worked["contributions"],
                deductions=worked["deductions"], net=worked["net"]))
            for line in worked["lines"]:
                self.store.payslip_lines.insert(PayslipLine(
                    id="", payslip_id=slip.id, element_id=line["element_id"],
                    kind="payment", hours=line["hours"], amount=line["amount"]))
            for line in worked["deduction_lines"]:
                self.store.payslip_lines.insert(PayslipLine(
                    id="", payslip_id=slip.id, element_id=line["element_id"],
                    kind="deduction", hours=0, amount=line["taken"]))
        return self.store.runs.update(row.id, status=COMMITTED,
                                      committed_on=committed_on)

    def abandon(self, operator: Operator, run_id: str) -> PayrollRun:
        row = self.get(operator, run_id)
        if not is_open(row):
            raise conflict(f"that run was already {row.status}")
        return self.store.runs.update(row.id, status="abandoned")

    def totals(self, operator: Operator, run_id: str) -> dict:
        row = self.get(operator, run_id)
        slips = [slip for slip in self.store.payslips.all() if slip.run_id == row.id]
        return {"run_id": row.id, "status": row.status,
                "headcount": headcount(slips), "gross": gross_total(slips),
                "revenue": revenue_total(slips), "net": run_total(slips)}
