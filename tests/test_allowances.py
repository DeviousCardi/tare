"""Allowances: the flat sums somebody is paid every period."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_allowances, seed_elements,
    seed_employees, seed_employers,
)
from tare.common.types import Allowance
from tare.modules.allowances.rules import (
    by_element, comes_to, sort_by_start, standing_for, stands_on,
)
from tare.modules.allowances.schemas import AwardAllowance, EndAllowance, ListAllowances
from tare.modules.allowances.service import AllowancesService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_elements, seed_allowances):
        seed(store)
    return store


def service():
    return AllowancesService(a_store())


def an_allowance(**kw) -> Allowance:
    base = dict(id="al-9", employee_id="ee-1", employer_id="em-1", element_id="el-3",
                amount=4500, starts_on="2025-01-01", ends_on=None)
    return Allowance(**{**base, **kw})


def test_allowances_read_earliest_first():
    rows = sort_by_start([an_allowance(starts_on="2025-07-01"),
                          an_allowance(starts_on="2025-01-01")])
    assert [row.starts_on for row in rows] == ["2025-01-01", "2025-07-01"]


def test_an_allowance_stands_on_the_day_it_starts():
    assert stands_on(an_allowance(starts_on="2025-01-01"), "2025-01-01") is True


def test_an_allowance_does_not_stand_the_day_before_it_starts():
    assert stands_on(an_allowance(starts_on="2025-01-01"), "2024-12-31") is False


def test_an_allowance_still_stands_on_the_day_it_ends():
    assert stands_on(an_allowance(ends_on="2025-06-30"), "2025-06-30") is True


def test_an_allowance_does_not_stand_the_day_after_it_ends():
    assert stands_on(an_allowance(ends_on="2025-06-30"), "2025-07-01") is False


def test_the_allowances_somebody_is_on_are_found():
    found = standing_for(a_store().allowances.all(), "ee-1", "2025-06-01")
    assert [row.id for row in found] == ["al-1"]


def test_an_allowance_that_has_ended_is_no_longer_standing():
    assert standing_for(a_store().allowances.all(), "ee-2", "2025-11-01") == []


def test_allowances_come_to_their_sum():
    assert comes_to([an_allowance(amount=4500), an_allowance(id="b", amount=2000)]) == 6500


def test_no_allowances_come_to_nothing():
    assert comes_to([]) == 0


def test_allowances_split_by_what_they_are_paid_as():
    rows = [an_allowance(element_id="el-3", amount=4500),
            an_allowance(id="b", element_id="el-2", amount=2000)]
    assert by_element(rows) == {"el-2": 2000, "el-3": 4500}


def test_two_allowances_on_one_element_fold_together():
    rows = [an_allowance(amount=4500), an_allowance(id="b", amount=2000)]
    assert by_element(rows) == {"el-3": 6500}


def test_the_bureau_lists_every_allowance():
    assert service().list(BUREAU, ListAllowances())["total"] == 3


def test_a_manager_lists_only_their_own_employers_allowances():
    assert service().list(MANAGER, ListAllowances())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_day():
    assert service().list(MANAGER, ListAllowances(standing_on="2025-08-01"))["total"] == 2


def test_an_allowance_can_be_read():
    assert service().get(MANAGER, "al-1").amount == 4500


def test_an_allowance_nobody_awarded_is_missing():
    with pytest.raises(NotFound, match="allowance al-9 was not found"):
        service().get(BUREAU, "al-9")


def test_a_manager_cannot_read_another_employers_allowance():
    with pytest.raises(Refused):
        service().get(MANAGER, "al-3")


def test_an_allowance_is_awarded():
    row = service().award(MANAGER, AwardAllowance(
        employee_id="ee-3", element_id="el-3", amount=3000, starts_on="2025-01-01"))
    assert row.amount == 3000


def test_an_allowance_must_be_paid_as_a_payment():
    with pytest.raises(Refused, match="paid as a payment element"):
        service().award(MANAGER, AwardAllowance(
            employee_id="ee-3", element_id="el-4", amount=3000, starts_on="2025-01-01"))


def test_an_allowance_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().award(MANAGER, AwardAllowance(
            employee_id="ee-3", element_id="el-3", amount=3000,
            starts_on="2025-06-01", ends_on="2025-01-01"))


def test_a_second_allowance_over_one_already_standing_is_refused():
    with pytest.raises(Conflict, match="already has EXP"):
        service().award(MANAGER, AwardAllowance(
            employee_id="ee-1", element_id="el-3", amount=1, starts_on="2025-06-01"))


def test_an_allowance_is_ended():
    assert service().end(MANAGER, "al-1", EndAllowance(ends_on="2025-09-30")).ends_on == "2025-09-30"


def test_an_allowance_cannot_end_twice():
    with pytest.raises(Conflict, match="already ended"):
        service().end(MANAGER, "al-2", EndAllowance(ends_on="2025-10-31"))


def test_what_somebody_is_on_is_reported():
    answer = service().standing(MANAGER, "ee-1", "2025-06-01")
    assert answer["comes_to"] == 4500 and answer["by_element"] == {"el-3": 4500}


def test_somebody_on_nothing_comes_to_nothing():
    assert service().standing(MANAGER, "ee-3", "2025-06-01")["comes_to"] == 0


def client():
    return build_client(a_store())


def test_the_route_lists_allowances():
    assert client().get("/allowances", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_what_somebody_is_on():
    answer = client().get("/allowances/standing/ee-1?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["comes_to"] == 4500


def test_the_route_awards_an_allowance_and_answers_201():
    answer = client().post("/allowances", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "element_id": "el-3", "amount": 3000,
        "starts_on": "2025-01-01"})
    assert answer.status_code == 201


def test_the_route_ends_an_allowance():
    answer = client().post("/allowances/al-1/end", headers=headers(MANAGER),
                           json={"ends_on": "2025-09-30"})
    assert answer.json()["ends_on"] == "2025-09-30"
