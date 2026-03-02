"""Earnings orders: what a court has told us to take out of somebody's pay."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_orders,
)
from tare.common.types import EarningsOrder
from tare.modules.orders.rules import (
    by_priority, due_now, is_live, live_orders, periods_left, remaining,
)
from tare.modules.orders.schemas import (
    CollectOnOrder, DischargeOrder, ListOrders, ServeOrder,
)
from tare.modules.orders.service import OrdersService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_orders):
        seed(store)
    return store


def service():
    return OrdersService(a_store())


def an_order(**kw) -> EarningsOrder:
    base = dict(id="or-9", employee_id="ee-1", employer_id="em-1",
                reference="CT/2025/0009", total=60000, per_period=5000,
                collected=15000, priority=10, made_on="2025-02-01",
                discharged_on=None)
    return EarningsOrder(**{**base, **kw})


def test_orders_are_worked_in_priority_order():
    rows = by_priority([an_order(id="b", priority=20), an_order(id="a", priority=10)])
    assert [row.id for row in rows] == ["a", "b"]


def test_orders_of_one_priority_are_worked_oldest_first():
    rows = by_priority([an_order(id="b", made_on="2025-06-01"),
                        an_order(id="a", made_on="2025-01-01")])
    assert [row.id for row in rows] == ["a", "b"]


def test_an_order_with_something_left_is_live():
    assert is_live(an_order(total=60000, collected=15000)) is True


def test_an_order_that_has_collected_its_total_is_no_longer_live():
    assert is_live(an_order(total=60000, collected=60000)) is False


def test_a_discharged_order_is_no_longer_live():
    assert is_live(an_order(discharged_on="2025-06-01")) is False


def test_what_is_left_is_the_total_less_what_was_collected():
    assert remaining(an_order(total=60000, collected=15000)) == 45000


def test_an_order_collected_in_full_has_nothing_left():
    assert remaining(an_order(total=60000, collected=60000)) == 0


def test_an_order_over_collected_still_has_nothing_left_rather_than_less():
    assert remaining(an_order(total=60000, collected=70000)) == 0


# Every order below still owes at least what it asks for each period, which is
# every period but the last, so what it asks for does not depend on how the
# final part-period is treated.
def test_a_live_order_asks_for_what_it_asks_each_period():
    assert due_now(an_order(total=60000, collected=15000, per_period=5000)) == 5000


def test_an_order_owing_exactly_one_period_asks_for_that_period():
    assert due_now(an_order(total=60000, collected=55000, per_period=5000)) == 5000


def test_an_order_that_is_no_longer_live_asks_for_nothing():
    assert due_now(an_order(total=60000, collected=60000)) == 0


def test_a_discharged_order_asks_for_nothing():
    assert due_now(an_order(discharged_on="2025-06-01")) == 0


def test_the_periods_left_follow_what_is_still_owed():
    assert periods_left(an_order(total=60000, collected=15000, per_period=5000)) == 9


def test_a_part_period_still_counts_as_a_period():
    assert periods_left(an_order(total=60000, collected=57000, per_period=5000)) == 1


def test_an_order_that_is_finished_has_no_periods_left():
    assert periods_left(an_order(total=60000, collected=60000)) == 0


def test_the_live_orders_for_somebody_are_found():
    assert [row.id for row in live_orders(a_store().orders.all(), "ee-1")] == ["or-1"]


def test_somebody_whose_orders_are_all_collected_has_none_live():
    assert live_orders(a_store().orders.all(), "ee-2") == []


def test_the_bureau_lists_every_order():
    assert service().list(BUREAU, ListOrders())["total"] == 3


def test_a_manager_lists_only_their_own_employers_orders():
    assert service().list(MANAGER, ListOrders())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_still_live():
    assert service().list(MANAGER, ListOrders(live_only=True))["total"] == 1


def test_an_order_can_be_read():
    assert service().get(MANAGER, "or-1").reference == "CT/2025/0001"


def test_an_order_nobody_served_is_missing():
    with pytest.raises(NotFound, match="order or-9 was not found"):
        service().get(BUREAU, "or-9")


def test_a_manager_cannot_read_another_employers_order():
    with pytest.raises(Refused):
        service().get(MANAGER, "or-3")


def test_an_order_is_served():
    row = service().serve(MANAGER, ServeOrder(
        employee_id="ee-3", reference="CT/2025/0009", total=20000,
        per_period=2000, made_on="2025-05-01"))
    assert row.collected == 0


def test_an_order_cannot_ask_for_more_each_period_than_it_is_for():
    with pytest.raises(Refused, match="more each period than it is for"):
        service().serve(MANAGER, ServeOrder(
            employee_id="ee-3", reference="CT/2025/0009", total=2000,
            per_period=20000, made_on="2025-05-01"))


def test_a_reference_already_served_is_refused():
    with pytest.raises(Conflict, match="has already been served"):
        service().serve(MANAGER, ServeOrder(
            employee_id="ee-3", reference="CT/2025/0001", total=20000,
            per_period=2000, made_on="2025-05-01"))


def test_something_is_collected_against_an_order():
    assert service().collect(MANAGER, "or-1", CollectOnOrder(amount=5000)).collected == 20000


def test_an_order_cannot_collect_more_than_it_is_owed():
    with pytest.raises(Refused, match="more than it is still owed"):
        service().collect(MANAGER, "or-1", CollectOnOrder(amount=50000))


def test_an_order_that_is_finished_cannot_collect_again():
    with pytest.raises(Conflict, match="no longer live"):
        service().collect(MANAGER, "or-2", CollectOnOrder(amount=1000))


def test_an_order_is_discharged():
    answer = service().discharge(MANAGER, "or-1", DischargeOrder(discharged_on="2025-09-01"))
    assert answer.discharged_on == "2025-09-01"


def test_an_order_cannot_be_discharged_twice():
    svc = service()
    svc.discharge(MANAGER, "or-1", DischargeOrder(discharged_on="2025-09-01"))
    with pytest.raises(Conflict, match="already been discharged"):
        svc.discharge(MANAGER, "or-1", DischargeOrder(discharged_on="2025-10-01"))


def test_an_order_cannot_be_discharged_before_it_was_made():
    with pytest.raises(Refused, match="before it was made"):
        service().discharge(MANAGER, "or-1", DischargeOrder(discharged_on="2024-01-01"))


def test_the_state_of_an_order_is_reported():
    answer = service().state(MANAGER, "or-1")
    assert answer["remaining"] == 45000 and answer["due_now"] == 5000


def client():
    return build_client(a_store())


def test_the_route_lists_orders():
    assert client().get("/orders", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_the_live_orders_for_somebody():
    answer = client().get("/orders/live/ee-1", headers=headers(MANAGER))
    assert answer.json()["total"] == 1


def test_the_route_reports_the_state_of_an_order():
    answer = client().get("/orders/or-1/state", headers=headers(MANAGER))
    assert answer.json()["periods_left"] == 9


def test_the_route_serves_an_order_and_answers_201():
    answer = client().post("/orders", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "reference": "CT/2025/0009", "total": 20000,
        "per_period": 2000, "made_on": "2025-05-01"})
    assert answer.status_code == 201


def test_the_route_collects_against_an_order():
    answer = client().post("/orders/or-1/collect", headers=headers(MANAGER),
                           json={"amount": 5000})
    assert answer.json()["collected"] == 20000
