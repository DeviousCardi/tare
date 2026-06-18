"""Remittances, and getting them to the provider in time."""

from __future__ import annotations

from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Remittance
from tare.modules.employers.schemas import a_day
from tare.modules.providers.service import ProvidersService
from tare.modules.remittances.rules import (
    is_overdue, is_waiting, owed_to, sort_by_due, waiting,
)
from tare.modules.remittances.schemas import (
    ListRemittances, RaiseRemittance, SendRemittance,
)
from tare.modules.runs.service import RunsService


class RemittancesService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.runs = RunsService(store)
        self.providers = ProvidersService(store)

    def list(self, operator: Operator, query: ListRemittances) -> dict:
        rows = visible_to(operator, self.store.remittances.all())
        if query.run_id:
            rows = [row for row in rows if row.run_id == query.run_id]
        if query.provider_id:
            rows = [row for row in rows if row.provider_id == query.provider_id]
        if query.waiting_only:
            rows = waiting(rows)
        return page(sort_by_due(rows), query.limit, query.offset)

    def get(self, operator: Operator, remittance_id: str) -> Remittance:
        row = self.store.remittances.find(remittance_id)
        if not row:
            raise not_found("remittance", remittance_id)
        from tare.modules.employers.service import EmployersService

        EmployersService(self.store).assert_visible(operator, row.employer_id)
        return row

    def raise_it(self, operator: Operator, dto: RaiseRemittance) -> Remittance:
        run = self.runs.get(operator, dto.run_id)
        provider = self.providers.get(operator, dto.provider_id)
        if run.status != "committed":
            raise refuse("only a committed run has anything to remit")
        clash = self.store.remittances.first(
            lambda row: row.run_id == run.id and row.provider_id == provider.id)
        if clash:
            raise conflict(f"{provider.code} has already been raised for that run")
        return self.store.remittances.insert(Remittance(
            id="", run_id=run.id, employer_id=run.employer_id,
            provider_id=provider.id, amount=dto.amount,
            due_on=a_day(dto.due_on, "due_on"), sent_on=None))

    def send(
        self, operator: Operator, remittance_id: str, dto: SendRemittance,
    ) -> Remittance:
        row = self.get(operator, remittance_id)
        if not is_waiting(row):
            raise conflict("that remittance has already gone")
        sent_on = a_day(dto.sent_on, "sent_on")
        return self.store.remittances.update(row.id, sent_on=sent_on)

    def overdue(self, operator: Operator, on: str) -> list[Remittance]:
        day = a_day(on, "on")
        return [row for row in sort_by_due(visible_to(operator, self.store.remittances.all()))
                if is_overdue(row, day)]

    def owed(self, operator: Operator, provider_id: str) -> int:
        self.providers.get(operator, provider_id)
        return owed_to(visible_to(operator, self.store.remittances.all()), provider_id)
