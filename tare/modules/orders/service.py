"""Earnings orders, and collecting against one."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import visible_to
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import EarningsOrder, Operator
from tare.modules.employees.service import EmployeesService
from tare.modules.employers.schemas import a_day
from tare.modules.orders.rules import (
    by_priority, due_now, is_live, live_orders, periods_left, remaining,
)
from tare.modules.orders.schemas import (
    CollectOnOrder, DischargeOrder, ListOrders, ServeOrder,
)


class OrdersService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employees = EmployeesService(store)

    def list(self, operator: Operator, query: ListOrders) -> dict:
        rows = visible_to(operator, self.store.orders.all())
        if query.employee_id:
            self.employees.get(operator, query.employee_id)
            rows = [row for row in rows if row.employee_id == query.employee_id]
        if query.live_only:
            rows = [row for row in rows if is_live(row)]
        return page(by_priority(rows), query.limit, query.offset)

    def get(self, operator: Operator, order_id: str) -> EarningsOrder:
        row = self.store.orders.find(order_id)
        if not row:
            raise not_found("order", order_id)
        self.employees.get(operator, row.employee_id)
        return row

    def serve(self, operator: Operator, dto: ServeOrder) -> EarningsOrder:
        person = self.employees.get(operator, dto.employee_id)
        made_on = a_day(dto.made_on, "made_on")
        if dto.per_period > dto.total:
            raise refuse("an order cannot ask for more each period than it is for")
        if self.store.orders.first(lambda row: row.reference == dto.reference):
            raise conflict(f"order {dto.reference} has already been served")
        return self.store.orders.insert(EarningsOrder(
            id="", employee_id=person.id, employer_id=person.employer_id,
            reference=dto.reference, total=dto.total, per_period=dto.per_period,
            collected=0, priority=dto.priority, made_on=made_on,
            discharged_on=None))

    def collect(
        self, operator: Operator, order_id: str, dto: CollectOnOrder,
    ) -> EarningsOrder:
        row = self.get(operator, order_id)
        if not is_live(row):
            raise conflict("that order is no longer live")
        if dto.amount > remaining(row):
            raise refuse("an order cannot collect more than it is still owed")
        return self.store.orders.update(row.id, collected=row.collected + dto.amount)

    def discharge(
        self, operator: Operator, order_id: str, dto: DischargeOrder,
    ) -> EarningsOrder:
        row = self.get(operator, order_id)
        discharged_on = a_day(dto.discharged_on, "discharged_on")
        if row.discharged_on is not None:
            raise conflict("that order has already been discharged")
        if compare_dates(discharged_on, row.made_on) < 0:
            raise refuse("an order cannot be discharged before it was made")
        return self.store.orders.update(row.id, discharged_on=discharged_on)

    def state(self, operator: Operator, order_id: str) -> dict:
        row = self.get(operator, order_id)
        return {"order_id": row.id, "live": is_live(row), "remaining": remaining(row),
                "due_now": due_now(row), "periods_left": periods_left(row)}

    def live_for(self, operator: Operator, employee_id: str) -> list[EarningsOrder]:
        self.employees.get(operator, employee_id)
        return live_orders(self.store.orders.all(), employee_id)
