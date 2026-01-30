"""Payslips, and reading what a year has come to so far."""

from __future__ import annotations

from tare.common.errors import not_found
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Payslip
from tare.modules.employees.service import EmployeesService
from tare.modules.payslips.rules import (
    balances, lines_come_to, sort_by_period, sort_lines, year_to_date,
)
from tare.modules.payslips.schemas import ListPayslips


class PayslipsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListPayslips) -> dict:
        rows = visible_to(operator, self.store.payslips.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.run_id:
            rows = [row for row in rows if row.run_id == query.run_id]
        if query.period is not None:
            rows = [row for row in rows if row.period == query.period]
        return page(sort_by_period(rows), query.limit, query.offset)

    def get(self, operator: Operator, payslip_id: str) -> Payslip:
        row = self.store.payslips.find(payslip_id)
        if not row:
            raise not_found("payslip", payslip_id)
        self.employees.get(operator, row.employee_id)
        return row

    def lines(self, operator: Operator, payslip_id: str) -> list:
        self.get(operator, payslip_id)
        return sort_lines([row for row in self.store.payslip_lines.all()
                           if row.payslip_id == payslip_id])

    def with_lines(self, operator: Operator, payslip_id: str) -> dict:
        row = self.get(operator, payslip_id)
        lines = self.lines(operator, payslip_id)
        return {"payslip": row, "lines": lines,
                "payments": lines_come_to(lines, "payment"),
                "deductions": lines_come_to(lines, "deduction"),
                "balances": balances(row)}

    def year_to_date(self, operator: Operator, employee_id: str, period: int) -> dict:
        self.employees.get(operator, employee_id)
        mine = [row for row in self.store.payslips.all()
                if row.employee_id == employee_id]
        return {"employee_id": employee_id, "upto_period": period,
                **year_to_date(mine, period)}
