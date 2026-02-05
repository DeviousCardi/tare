"""Registers, read off a run's payslips."""

from __future__ import annotations

from tare.common.errors import refuse
from tare.common.store import Store
from tare.common.types import Operator
from tare.modules.positions.rules import held_by
from tare.modules.registers.rules import gather, totals_of
from tare.modules.runs.service import RunsService

#: What a register may be gathered by.
BY_EMPLOYEE = "employee"
BY_DEPARTMENT = "department"
BY_COST_CENTRE = "cost_centre"
GROUPINGS = (BY_EMPLOYEE, BY_DEPARTMENT, BY_COST_CENTRE)


class RegistersService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.runs = RunsService(store)

    def of(self, operator: Operator, run_id: str, grouped_by: str) -> dict:
        run = self.runs.get(operator, run_id)
        if grouped_by not in GROUPINGS:
            raise refuse(f"a register cannot be gathered by {grouped_by}")
        slips = [row for row in self.store.payslips.all() if row.run_id == run.id]
        posts = self.store.positions.all()

        def key_of(slip) -> str:
            if grouped_by == BY_EMPLOYEE:
                return slip.employee_id
            post = held_by(posts, slip.employee_id, slip.end)
            if post is None:
                return "unposted"
            return post.department_id if grouped_by == BY_DEPARTMENT \
                else post.cost_centre_id

        lines = gather(slips, key_of)
        return {"run_id": run.id, "grouped_by": grouped_by,
                "lines": [line.__dict__ for line in lines],
                "totals": totals_of(lines).__dict__}
