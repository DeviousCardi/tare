"""Transfers, and what goes across with somebody."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, ServiceTransfer
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.transfers.rules import (
    KINDS, is_accepted, moves_to, service_carries, sort_by_effective,
)
from tare.modules.transfers.schemas import (
    AcceptTransfer, ListTransfers, ProposeTransfer,
)


class TransfersService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListTransfers) -> dict:
        rows = [row for row in self.store.transfers.all()
                if operator.role == "bureau"
                or operator.employer_id in (row.from_employer_id, row.to_employer_id)]
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.to_employer_id:
            rows = [row for row in rows if row.to_employer_id == query.to_employer_id]
        if query.accepted_only:
            rows = [row for row in rows if is_accepted(row)]
        return page(sort_by_effective(rows), query.limit, query.offset)

    def get(self, operator: Operator, transfer_id: str) -> ServiceTransfer:
        row = self.store.transfers.find(transfer_id)
        if not row:
            raise not_found("transfer", transfer_id)
        if operator.role != "bureau" and operator.employer_id not in (
                row.from_employer_id, row.to_employer_id):
            raise refuse(f"{operator.name} cannot see that transfer")
        return row

    def propose(self, operator: Operator, dto: ProposeTransfer) -> ServiceTransfer:
        person = self.employees.get(operator, dto.employee_id)
        # Only that the destination is on the books, not that this operator can
        # see it: somebody transferring out goes to an employer whose payroll is
        # none of their own manager's business.
        if not self.store.employers.find(dto.to_employer_id):
            raise not_found("employer", dto.to_employer_id)
        if dto.kind not in KINDS:
            raise refuse(f"{dto.kind} is not a kind of transfer this service knows")
        if dto.to_employer_id == person.employer_id:
            raise refuse("a transfer must move somebody somewhere else")
        effective_on = a_day(dto.effective_on, "effective_on")
        standing = self.store.transfers.first(
            lambda row: row.employee_id == person.id and row.accepted_on is None)
        if standing:
            raise conflict(f"{person.reference} already has a transfer waiting")
        return self.store.transfers.insert(ServiceTransfer(
            id="", employee_id=person.id, from_employer_id=person.employer_id,
            to_employer_id=dto.to_employer_id, kind=dto.kind,
            effective_on=effective_on, accepted_on=None))

    def accept(
        self, operator: Operator, transfer_id: str, dto: AcceptTransfer,
    ) -> ServiceTransfer:
        row = self.get(operator, transfer_id)
        accepted_on = a_day(dto.accepted_on, "accepted_on")
        if is_accepted(row):
            raise conflict("that transfer has already been accepted")
        if compare_dates(accepted_on, row.effective_on) > 0:
            raise refuse("a transfer cannot be accepted after it takes effect")
        self.store.employees.update(row.employee_id, employer_id=row.to_employer_id)
        return self.store.transfers.update(row.id, accepted_on=accepted_on)

    def carries(self, operator: Operator, transfer_id: str) -> dict:
        row = self.get(operator, transfer_id)
        return {"transfer_id": row.id, "kind": row.kind,
                "service_carries": service_carries(row)}

    def where(self, operator: Operator, employee_id: str) -> str | None:
        self.employees.get(operator, employee_id)
        return moves_to(self.store.transfers.all(), employee_id)
