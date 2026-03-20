"""Payment instructions, and getting the money out of the door."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, PaymentInstruction
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.mandates.service import MandatesService
from tare.modules.payments.rules import (
    FAILED, ISSUED, SETTLED, failed_total, is_live, outstanding_total, settled_total,
    sort_by_issue,
)
from tare.modules.payments.schemas import (
    FailPayment, IssuePayment, ListPayments, SettlePayment,
)
from tare.modules.runs.service import RunsService


class PaymentsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.mandates = MandatesService(store)
        self.runs = RunsService(store)

    def list(self, operator: Operator, query: ListPayments) -> dict:
        rows = visible_to(operator, self.store.payments.all())
        if query.run_id:
            rows = [row for row in rows if row.run_id == query.run_id]
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.status:
            rows = [row for row in rows if row.status == query.status]
        return page(sort_by_issue(rows), query.limit, query.offset)

    def get(self, operator: Operator, payment_id: str) -> PaymentInstruction:
        row = self.store.payments.find(payment_id)
        if not row:
            raise not_found("payment", payment_id)
        self.employees.get(operator, row.employee_id)
        return row

    def issue(self, operator: Operator, dto: IssuePayment) -> PaymentInstruction:
        person = self.employees.get(operator, dto.employee_id)
        run = self.runs.get(operator, dto.run_id)
        if run.status != "committed":
            raise refuse("a run must be committed before it can be paid")
        issued_on = a_day(dto.issued_on, "issued_on")
        mandate = self.mandates.standing(operator, person.id, issued_on)
        clash = self.store.payments.first(
            lambda row: row.run_id == run.id and row.employee_id == person.id
            and row.status != "cancelled")
        if clash:
            raise conflict(f"{person.reference} has already been paid for that run")
        return self.store.payments.insert(PaymentInstruction(
            id="", run_id=run.id, employee_id=person.id,
            employer_id=person.employer_id, account=mandate.account,
            amount=dto.amount, status=ISSUED, issued_on=issued_on,
            settled_on=None))

    def settle(
        self, operator: Operator, payment_id: str, dto: SettlePayment,
    ) -> PaymentInstruction:
        row = self.get(operator, payment_id)
        if not is_live(row):
            raise conflict(f"that payment was already {row.status}")
        settled_on = a_day(dto.settled_on, "settled_on")
        if compare_dates(settled_on, row.issued_on) < 0:
            raise refuse("a payment cannot settle before it was issued")
        return self.store.payments.update(row.id, status=SETTLED,
                                          settled_on=settled_on)

    def fail(
        self, operator: Operator, payment_id: str, dto: FailPayment,
    ) -> PaymentInstruction:
        row = self.get(operator, payment_id)
        if not is_live(row):
            raise conflict(f"that payment was already {row.status}")
        return self.store.payments.update(row.id, status=FAILED)

    def cancel(self, operator: Operator, payment_id: str) -> PaymentInstruction:
        row = self.get(operator, payment_id)
        if not is_live(row):
            raise conflict(f"that payment was already {row.status}")
        return self.store.payments.update(row.id, status="cancelled")

    def for_run(self, operator: Operator, run_id: str) -> dict:
        run = self.runs.get(operator, run_id)
        rows = [row for row in self.store.payments.all() if row.run_id == run.id]
        return {"run_id": run.id, "settled": settled_total(rows),
                "failed": failed_total(rows),
                "outstanding": outstanding_total(rows)}
