"""Routes for earnings orders."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.orders.schemas import (
    CollectOnOrder, DischargeOrder, ListOrders, OrderOut, OrderStateOut, ServeOrder,
)
from tare.modules.orders.service import OrdersService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
def list_orders(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    live_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = OrdersService(store).list(operator, ListOrders(
        employee_id=employee_id, live_only=live_only, limit=limit, offset=offset))
    return {"data": [OrderOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/live/{employee_id}")
def live_orders(employee_id: str, operator: TheOperator, store: TheStore) -> dict:
    rows = OrdersService(store).live_for(operator, employee_id)
    return {"employee_id": employee_id,
            "data": [OrderOut.of(row) for row in rows], "total": len(rows)}


@router.get("/{order_id}")
def get_order(order_id: str, operator: TheOperator, store: TheStore) -> OrderOut:
    return OrderOut.of(OrdersService(store).get(operator, order_id))


@router.get("/{order_id}/state")
def order_state(order_id: str, operator: TheOperator, store: TheStore) -> OrderStateOut:
    return OrderStateOut(**OrdersService(store).state(operator, order_id))


@router.post("", status_code=201)
def serve_order(dto: ServeOrder, operator: TheOperator, store: TheStore) -> OrderOut:
    return OrderOut.of(OrdersService(store).serve(operator, dto))


@router.post("/{order_id}/collect")
def collect_on_order(
    order_id: str, dto: CollectOnOrder, operator: TheOperator, store: TheStore,
) -> OrderOut:
    return OrderOut.of(OrdersService(store).collect(operator, order_id, dto))


@router.post("/{order_id}/discharge")
def discharge_order(
    order_id: str, dto: DischargeOrder, operator: TheOperator, store: TheStore,
) -> OrderOut:
    return OrderOut.of(OrdersService(store).discharge(operator, order_id, dto))
