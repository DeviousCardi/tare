"""Balances: what a deduction could not take, held over."""

import pytest

from tare.common.errors import Conflict, NotFound
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_balances, seed_elements,
    seed_employees, seed_employers,
)
from tare.common.types import CarriedBalance
from tare.modules.balances.rules import (
    CARRY_CEILING, is_open, open_balances, outstanding, sort_by_period, to_carry,
)
from tare.modules.balances.schemas import ClearBalance, HoldOver, ListBalances
from tare.modules.balances.service import BalancesService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_elements, seed_balances):
        seed(store)
    return store


def service():
    return BalancesService(a_store())


def a_balance(**kw) -> CarriedBalance:
    base = dict(id="bl-9", employee_id="ee-1", employer_id="em-1", element_id="el-4",
                year_starts_on="2025-04-06", period=3, shortfall=1500,
                carried=1500, cleared_on=None)
    return CarriedBalance(**{**base, **kw})


def test_balances_read_by_period():
    rows = sort_by_period([a_balance(period=3), a_balance(period=2)])
    assert [row.period for row in rows] == [2, 3]


def test_a_balance_nobody_cleared_is_open():
    assert is_open(a_balance(cleared_on=None)) is True


def test_a_cleared_balance_is_no_longer_open():
    assert is_open(a_balance(cleared_on="2025-07-28")) is False


# Every shortfall below is well inside the ceiling a single period may carry,
# which is what an ordinary shortfall looks like, so what goes forward does not
# depend on how one larger than the ceiling is treated.
def test_a_shortfall_carries_forward_whole():
    assert to_carry(1500) == 1500


def test_a_smaller_shortfall_carries_forward_whole_too():
    assert to_carry(900) == 900


def test_no_shortfall_carries_nothing():
    assert to_carry(0) == 0


def test_a_negative_shortfall_carries_nothing():
    assert to_carry(-500) == 0


def test_a_shortfall_exactly_on_the_ceiling_carries_forward_whole():
    assert to_carry(CARRY_CEILING) == CARRY_CEILING


def test_what_is_outstanding_adds_the_open_balances_up():
    assert outstanding(a_store().balances.all(), "ee-1", "el-4") == 1500


def test_a_cleared_balance_is_no_longer_outstanding():
    assert outstanding(a_store().balances.all(), "ee-2", "el-4") == 0


def test_somebody_with_nothing_held_over_owes_nothing():
    assert outstanding(a_store().balances.all(), "ee-3", "el-4") == 0


def test_the_open_balances_for_somebody_are_found():
    assert [row.id for row in open_balances(a_store().balances.all(), "ee-1")] == ["bl-1"]


def test_somebody_whose_balances_are_cleared_has_none_open():
    assert open_balances(a_store().balances.all(), "ee-2") == []


def test_the_bureau_lists_every_balance():
    assert service().list(BUREAU, ListBalances())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_still_open():
    assert service().list(MANAGER, ListBalances(open_only=True))["total"] == 1


def test_a_balance_can_be_read():
    assert service().get(MANAGER, "bl-1").carried == 1500


def test_a_balance_nobody_held_is_missing():
    with pytest.raises(NotFound, match="balance bl-9 was not found"):
        service().get(BUREAU, "bl-9")


def test_a_shortfall_is_held_over():
    row = service().hold_over(MANAGER, HoldOver(
        employee_id="ee-3", element_id="el-4", year_starts_on="2025-04-06",
        period=4, shortfall=1200))
    assert row.carried == 1200 and row.cleared_on is None


def test_a_second_balance_from_one_period_is_refused():
    with pytest.raises(Conflict, match="already has a balance held from period"):
        service().hold_over(MANAGER, HoldOver(
            employee_id="ee-1", element_id="el-4", year_starts_on="2025-04-06",
            period=3, shortfall=100))


def test_a_balance_is_cleared():
    assert service() \
        .clear(MANAGER, "bl-1", ClearBalance(cleared_on="2025-08-28")).cleared_on == "2025-08-28"


def test_a_balance_cannot_be_cleared_twice():
    with pytest.raises(Conflict, match="already been cleared"):
        service().clear(MANAGER, "bl-2", ClearBalance(cleared_on="2025-08-28"))


def test_clearing_a_balance_takes_it_out_of_what_is_outstanding():
    svc = service()
    svc.clear(MANAGER, "bl-1", ClearBalance(cleared_on="2025-08-28"))
    assert svc.outstanding(MANAGER, "ee-1", "el-4") == 0


def test_what_is_outstanding_is_reported():
    assert service().outstanding(MANAGER, "ee-1", "el-4") == 1500


def client():
    return build_client(a_store())


def test_the_route_lists_balances():
    assert client().get("/balances", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_reports_what_is_outstanding():
    answer = client().get("/balances/outstanding/ee-1?element_id=el-4",
                          headers=headers(MANAGER))
    assert answer.json()["outstanding"] == 1500


def test_the_route_holds_a_shortfall_over_and_answers_201():
    answer = client().post("/balances", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "element_id": "el-4",
        "year_starts_on": "2025-04-06", "period": 4, "shortfall": 1200})
    assert answer.status_code == 201


def test_the_route_clears_a_balance():
    answer = client().post("/balances/bl-1/clear", headers=headers(MANAGER),
                           json={"cleared_on": "2025-08-28"})
    assert answer.json()["cleared_on"] == "2025-08-28"
