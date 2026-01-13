"""Suspensions: the periods a deduction is held off somebody's pay."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_elements, seed_employees,
    seed_employers, seed_suspensions,
)
from tare.common.types import Suspension
from tare.modules.suspensions.rules import (
    covers, is_open, periods_covered, sort_by_period, suspended_elements,
)
from tare.modules.suspensions.schemas import (
    ListSuspensions, LiftSuspension, SuspendDeduction,
)
from tare.modules.suspensions.service import SuspensionsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_elements(store)
    seed_suspensions(store)
    return store


def service():
    return SuspensionsService(a_store())


def a_suspension(**kw) -> Suspension:
    base = dict(id="su-9", employee_id="ee-1", employer_id="em-1", element_id="el-4",
                reason="no pay to take it from", from_period=3, to_period=None,
                year_starts_on="2025-04-06")
    return Suspension(**{**base, **kw})


def test_suspensions_read_earliest_period_first():
    rows = sort_by_period([a_suspension(from_period=5), a_suspension(from_period=1)])
    assert [row.from_period for row in rows] == [1, 5]


def test_a_suspension_covers_the_period_it_starts_in():
    assert covers(a_suspension(from_period=3), 3, "2025-04-06") is True


def test_a_suspension_does_not_cover_the_period_before_it_starts():
    assert covers(a_suspension(from_period=3), 2, "2025-04-06") is False


def test_an_open_suspension_covers_every_period_after_it_starts():
    assert covers(a_suspension(from_period=3), 12, "2025-04-06") is True


def test_a_lifted_suspension_still_covers_the_period_it_was_lifted_in():
    assert covers(a_suspension(from_period=1, to_period=2), 2, "2025-04-06") is True


def test_a_lifted_suspension_does_not_cover_the_period_after():
    assert covers(a_suspension(from_period=1, to_period=2), 3, "2025-04-06") is False


def test_a_suspension_in_another_year_covers_nothing_in_this_one():
    assert covers(a_suspension(from_period=3), 3, "2024-04-06") is False


def test_a_suspension_nobody_lifted_is_open():
    assert is_open(a_suspension()) is True


def test_a_lifted_suspension_is_no_longer_open():
    assert is_open(a_suspension(to_period=5)) is False


def test_an_open_suspension_runs_to_the_end_of_the_year():
    assert periods_covered(a_suspension(from_period=3), 12) == 10


def test_a_lifted_suspension_counts_the_periods_it_ran():
    assert periods_covered(a_suspension(from_period=1, to_period=2), 12) == 2


def test_a_suspension_lifted_in_the_period_it_started_ran_one_period():
    assert periods_covered(a_suspension(from_period=3, to_period=3), 12) == 1


def test_the_elements_held_off_somebodys_pay_are_reported():
    rows = a_store().suspensions.all()
    assert suspended_elements(rows, "ee-1", 5, "2025-04-06") == ["el-4"]


def test_nothing_is_held_off_before_a_suspension_starts():
    rows = a_store().suspensions.all()
    assert suspended_elements(rows, "ee-1", 1, "2025-04-06") == []


def test_nothing_is_held_off_after_a_suspension_is_lifted():
    rows = a_store().suspensions.all()
    assert suspended_elements(rows, "ee-2", 5, "2025-04-06") == []


def test_the_bureau_lists_every_suspension():
    assert service().list(BUREAU, ListSuspensions())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_still_running():
    assert service().list(MANAGER, ListSuspensions(open_only=True))["total"] == 1


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListSuspensions(employee_id="ee-1"))["total"] == 1


def test_a_suspension_can_be_read():
    assert service().get(MANAGER, "su-1").reason == "no pay to take it from"


def test_a_suspension_nobody_made_is_missing():
    with pytest.raises(NotFound, match="suspension su-9 was not found"):
        service().get(BUREAU, "su-9")


def test_a_deduction_is_suspended():
    row = service().suspend(MANAGER, SuspendDeduction(
        employee_id="ee-3", element_id="el-4", reason="the employee asked",
        from_period=1, year_starts_on="2025-04-06"))
    assert row.to_period is None


def test_only_a_deduction_can_be_suspended():
    with pytest.raises(Refused, match="only a deduction can be suspended"):
        service().suspend(MANAGER, SuspendDeduction(
            employee_id="ee-3", element_id="el-1", reason="the employee asked",
            from_period=1, year_starts_on="2025-04-06"))


def test_a_reason_the_service_does_not_hold_is_refused():
    with pytest.raises(Refused, match="is not a reason a deduction is suspended for"):
        service().suspend(MANAGER, SuspendDeduction(
            employee_id="ee-3", element_id="el-4", reason="just because",
            from_period=1, year_starts_on="2025-04-06"))


def test_a_second_suspension_over_one_already_running_is_refused():
    with pytest.raises(Conflict, match="already suspended for period"):
        service().suspend(MANAGER, SuspendDeduction(
            employee_id="ee-1", element_id="el-4", reason="the employee asked",
            from_period=5, year_starts_on="2025-04-06"))


def test_a_suspension_is_lifted():
    assert service().lift(MANAGER, "su-1", LiftSuspension(to_period=6)).to_period == 6


def test_a_suspension_cannot_be_lifted_twice():
    with pytest.raises(Conflict, match="already been lifted"):
        service().lift(MANAGER, "su-2", LiftSuspension(to_period=6))


def test_a_suspension_cannot_lift_before_it_started():
    with pytest.raises(Refused, match="before the period it started in"):
        service().lift(MANAGER, "su-1", LiftSuspension(to_period=1))


def test_lifting_a_suspension_lets_the_deduction_run_again():
    svc = service()
    svc.lift(MANAGER, "su-1", LiftSuspension(to_period=6))
    assert svc.held_off(MANAGER, "ee-1", 7, "2025-04-06") == []


def client():
    return build_client(a_store())


def test_the_route_lists_suspensions():
    assert client().get("/suspensions", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_reports_what_is_held_off():
    answer = client().get("/suspensions/held-off/ee-1?period=5&year_starts_on=2025-04-06",
                          headers=headers(MANAGER))
    assert answer.json()["elements"] == ["el-4"]


def test_the_route_suspends_a_deduction_and_answers_201():
    answer = client().post("/suspensions", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "element_id": "el-4", "reason": "the employee asked",
        "from_period": 1, "year_starts_on": "2025-04-06"})
    assert answer.status_code == 201


def test_the_route_lifts_a_suspension():
    answer = client().post("/suspensions/su-1/lift", headers=headers(MANAGER),
                           json={"to_period": 6})
    assert answer.json()["to_period"] == 6
