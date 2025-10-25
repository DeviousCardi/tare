"""The terms people are employed on, and how they change."""

from tare.common.dates import add_days, compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Contract, Operator
from tare.modules.contracts.rules import (
    daily_pay, full_time_part, hourly_pay, in_force_for, in_force_on, service_days,
    sort_by_start, weekly_pay,
)
from tare.modules.contracts.schemas import ChangeTerms, EndContract, ListContracts, OpenContract
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService


class ContractsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListContracts) -> dict:
        rows = visible_to(operator, self.store.contracts.all())
        if query.employer_id:
            self.employers.assert_visible(operator, query.employer_id)
            rows = [row for row in rows if row.employer_id == query.employer_id]
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.in_force_on:
            day = a_day(query.in_force_on, "in_force_on")
            rows = [row for row in rows if in_force_on(row, day)]
        return page(sort_by_start(rows), query.limit, query.offset)

    def get(self, operator: Operator, contract_id: str) -> Contract:
        row = self.store.contracts.find(contract_id)
        if not row:
            raise not_found("contract", contract_id)
        self.employers.assert_visible(operator, row.employer_id)
        return row

    def in_force(self, operator: Operator, employee_id: str, day: str) -> Contract:
        """The contract governing somebody on a day, or a refusal saying none is."""
        self.employees.get(operator, employee_id)
        found = in_force_for(self.store.contracts.all(), employee_id, a_day(day, "day"))
        if not found:
            raise not_found("contract in force", f"{employee_id} on {day}")
        return found

    def open(self, operator: Operator, dto: OpenContract) -> Contract:
        person = self.employees.get(operator, dto.employee_id)
        started_on = a_day(dto.started_on, "started_on")
        if compare_dates(started_on, person.joined_on) < 0:
            raise refuse("a contract cannot start before the person joined")
        standing = in_force_for(self.store.contracts.all(), person.id, started_on)
        if standing:
            raise conflict(f"{person.reference} already holds a contract on {started_on}")
        return self.store.contracts.insert(Contract(
            id="", employee_id=person.id, employer_id=person.employer_id,
            started_on=started_on, ended_on=None, hours_per_week=dto.hours_per_week,
            annual_salary=dto.annual_salary, notice_weeks=dto.notice_weeks))

    def end(self, operator: Operator, contract_id: str, dto: EndContract) -> Contract:
        row = self.get(operator, contract_id)
        ended_on = a_day(dto.ended_on, "ended_on")
        if row.ended_on is not None:
            raise conflict("that contract has already ended")
        if compare_dates(ended_on, row.started_on) < 0:
            raise refuse("a contract cannot end before it started")
        return self.store.contracts.update(row.id, ended_on=ended_on)

    def change_terms(
        self, operator: Operator, employee_id: str, dto: ChangeTerms,
    ) -> Contract:
        """End what is in force the day before, and open the new terms.

        Terms never change in place: the old contract is what the person was
        paid under and a run for a closed period has to be able to find it.
        """
        from_day = a_day(dto.from_day, "from_day")
        standing = self.in_force(operator, employee_id, from_day)
        if standing.started_on == from_day:
            raise refuse("terms cannot change on the day the contract started")
        self.store.contracts.update(standing.id, ended_on=add_days(from_day, -1))
        return self.store.contracts.insert(Contract(
            id="", employee_id=standing.employee_id, employer_id=standing.employer_id,
            started_on=from_day, ended_on=None,
            hours_per_week=standing.hours_per_week if dto.hours_per_week is None
            else dto.hours_per_week,
            annual_salary=standing.annual_salary if dto.annual_salary is None
            else dto.annual_salary,
            notice_weeks=standing.notice_weeks if dto.notice_weeks is None
            else dto.notice_weeks))

    def terms(self, operator: Operator, contract_id: str, upto: str) -> dict:
        row = self.get(operator, contract_id)
        return {
            "contract_id": row.id,
            "weekly_pay": weekly_pay(row),
            "daily_pay": daily_pay(row),
            "hourly_pay": hourly_pay(row),
            "full_time_part": full_time_part(row),
            "service_days": service_days(row, a_day(upto, "upto")),
        }
