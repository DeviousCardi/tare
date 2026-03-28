"""Runs of service, and how long somebody has really been here."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, ServiceRecord
from tare.modules.continuity.rules import (
    continuous_from, service_days, service_years, sort_by_start,
)
from tare.modules.continuity.schemas import EndService, ListService, RecordService
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day


class ContinuityService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListService) -> dict:
        rows = visible_to(operator, self.store.service.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, record_id: str) -> ServiceRecord:
        row = self.store.service.find(record_id)
        if not row:
            raise not_found("service record", record_id)
        self.employees.get(operator, row.employee_id)
        return row

    def record(self, operator: Operator, dto: RecordService) -> ServiceRecord:
        person = self.employees.get(operator, dto.employee_id)
        started_on = a_day(dto.started_on, "started_on")
        open_run = self.store.service.first(
            lambda row: row.employee_id == person.id and row.ended_on is None)
        if open_run:
            raise conflict(f"{person.reference} already has a run of service open")
        return self.store.service.insert(ServiceRecord(
            id="", employee_id=person.id, employer_id=person.employer_id,
            started_on=started_on, ended_on=None, reason=dto.reason))

    def end(self, operator: Operator, record_id: str, dto: EndService) -> ServiceRecord:
        row = self.get(operator, record_id)
        ended_on = a_day(dto.ended_on, "ended_on")
        if row.ended_on is not None:
            raise conflict("that run of service has already ended")
        if compare_dates(ended_on, row.started_on) < 0:
            raise refuse("a run of service cannot end before it starts")
        return self.store.service.update(row.id, ended_on=ended_on)

    def of(self, operator: Operator, employee_id: str, upto: str) -> dict:
        self.employees.get(operator, employee_id)
        day = a_day(upto, "upto")
        rows = self.store.service.all()
        return {"employee_id": employee_id,
                "continuous_from": continuous_from(rows, employee_id), "upto": day,
                "days": service_days(rows, employee_id, day),
                "years": service_years(rows, employee_id, day)}
