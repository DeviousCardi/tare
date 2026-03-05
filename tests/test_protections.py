"""Protected earnings: the figure an order may not take somebody below."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_protections,
)
from tare.common.types import ProtectedEarnings
from tare.modules.protections.rules import (
    available_for_orders, breaches, most_takeable, sort_by_start, standing_for,
    stands_on,
)
from tare.modules.protections.schemas import (
    EndProtection, ListProtections, SetProtection,
)
from tare.modules.protections.service import ProtectionsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_protections):
        seed(store)
    return store


def service():
    return ProtectionsService(a_store())


def a_floor(**kw) -> ProtectedEarnings:
    base = dict(id="pr-9", employee_id="ee-1", employer_id="em-1", floor=120000,
                starts_on="2025-02-01", ends_on=None)
    return ProtectedEarnings(**{**base, **kw})


def test_floors_read_earliest_first():
    rows = sort_by_start([a_floor(starts_on="2025-06-01"), a_floor(starts_on="2025-02-01")])
    assert [row.starts_on for row in rows] == ["2025-02-01", "2025-06-01"]


def test_a_floor_stands_on_the_day_it_starts():
    assert stands_on(a_floor(starts_on="2025-02-01"), "2025-02-01") is True


def test_a_floor_does_not_stand_the_day_before_it_starts():
    assert stands_on(a_floor(starts_on="2025-02-01"), "2025-01-31") is False


def test_a_floor_still_stands_on_the_day_it_ends():
    assert stands_on(a_floor(ends_on="2025-06-30"), "2025-06-30") is True


def test_the_floor_somebody_is_on_is_found():
    assert standing_for(a_store().protections.all(), "ee-1", "2025-06-01").floor == 120000


def test_the_latest_floor_wins_where_two_cover_a_day():
    rows = [a_floor(id="a", starts_on="2025-02-01"), a_floor(id="b", starts_on="2025-06-01")]
    assert standing_for(rows, "ee-1", "2025-08-01").id == "b"


def test_nobody_is_on_a_floor_before_it_starts():
    assert standing_for(a_store().protections.all(), "ee-1", "2025-01-01") is None


# Every figure of pay below sits above the protected floor, which is the
# ordinary case, so what an order may reach does not depend on how pay that
# has already fallen below the floor is read.
def test_everything_above_the_floor_is_within_an_orders_reach():
    assert available_for_orders(200000, 120000) == 80000


def test_pay_exactly_on_the_floor_leaves_nothing_within_reach():
    assert available_for_orders(120000, 120000) == 0


def test_an_order_may_take_what_it_asked_for_when_the_pay_stretches():
    assert most_takeable(200000, 120000, 5000) == 5000


def test_an_order_takes_only_what_is_above_the_floor():
    assert most_takeable(200000, 120000, 90000) == 80000


def test_an_order_takes_nothing_when_the_pay_sits_on_the_floor():
    assert most_takeable(120000, 120000, 5000) == 0


def test_taking_what_leaves_the_pay_above_the_floor_does_not_breach_it():
    assert breaches(200000, 120000, 5000) is False


def test_taking_what_leaves_the_pay_exactly_on_the_floor_does_not_breach_it():
    assert breaches(200000, 120000, 80000) is False


def test_taking_more_than_the_pay_can_bear_breaches_the_floor():
    assert breaches(200000, 120000, 90000) is True


def test_the_bureau_lists_every_floor():
    assert service().list(BUREAU, ListProtections())["total"] == 2


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListProtections(employee_id="ee-1"))["total"] == 1


def test_a_floor_can_be_read():
    assert service().get(MANAGER, "pr-1").floor == 120000


def test_a_floor_nobody_set_is_missing():
    with pytest.raises(NotFound, match="protection pr-9 was not found"):
        service().get(BUREAU, "pr-9")


def test_a_floor_is_set():
    assert service().set(MANAGER, SetProtection(
        employee_id="ee-3", floor=80000, starts_on="2025-05-01")).floor == 80000


def test_a_second_floor_starting_the_same_day_is_refused():
    with pytest.raises(Conflict, match="already starts on"):
        service().set(MANAGER, SetProtection(
            employee_id="ee-1", floor=1, starts_on="2025-02-01"))


def test_a_floor_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().set(MANAGER, SetProtection(
            employee_id="ee-3", floor=80000, starts_on="2025-06-01",
            ends_on="2025-01-01"))


def test_a_floor_is_ended():
    assert service().end(MANAGER, "pr-1", EndProtection(ends_on="2025-09-30")).ends_on == "2025-09-30"


def test_a_floor_cannot_end_twice():
    svc = service()
    svc.end(MANAGER, "pr-1", EndProtection(ends_on="2025-09-30"))
    with pytest.raises(Conflict, match="already ended"):
        svc.end(MANAGER, "pr-1", EndProtection(ends_on="2025-10-31"))


def test_what_an_order_may_reach_is_reported():
    answer = service().reach(MANAGER, "ee-1", "2025-06-01", 200000, 5000)
    assert answer["takeable"] == 5000 and answer["breaches"] is False


def test_a_day_no_floor_covers_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="protection standing"):
        service().reach(MANAGER, "ee-1", "2025-01-01", 200000, 5000)


def test_negative_pay_is_refused():
    with pytest.raises(Refused, match="cannot be negative"):
        service().reach(MANAGER, "ee-1", "2025-06-01", -1, 5000)


def client():
    return build_client(a_store())


def test_the_route_lists_floors():
    assert client().get("/protections", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_reports_what_an_order_may_reach():
    answer = client().get("/protections/reach/ee-1?on=2025-06-01&pay=200000&asked=90000",
                          headers=headers(MANAGER))
    assert answer.json()["takeable"] == 80000


def test_the_route_sets_a_floor_and_answers_201():
    answer = client().post("/protections", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "floor": 80000, "starts_on": "2025-05-01"})
    assert answer.status_code == 201


def test_the_route_ends_a_floor():
    answer = client().post("/protections/pr-1/end", headers=headers(MANAGER),
                           json={"ends_on": "2025-09-30"})
    assert answer.json()["ends_on"] == "2025-09-30"
