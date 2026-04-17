"""Awards: what one person got out of a review."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_awards, seed_employees,
    seed_employers, seed_reviews,
)
from tare.common.types import PayAward
from tare.modules.awards.rules import (
    average_share, cost_of, new_salary, sort_by_employee, uplift_of,
)
from tare.modules.awards.schemas import ListAwards, MakeAward
from tare.modules.awards.service import AwardsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_reviews, seed_awards):
        seed(store)
    return store


def service():
    return AwardsService(a_store())


def an_award(**kw) -> PayAward:
    base = dict(id="aw-9", review_id="rv-1", employee_id="ee-1", employer_id="em-1",
                basis="share", amount=300, old_salary=3120000, new_salary=3213600)
    return PayAward(**{**base, **kw})


def test_awards_read_by_the_person_they_are_for():
    rows = sort_by_employee([an_award(id="b", employee_id="ee-3"),
                             an_award(id="a", employee_id="ee-1")])
    assert [row.employee_id for row in rows] == ["ee-1", "ee-3"]


def test_a_flat_award_adds_its_own_amount():
    assert uplift_of(2600000, "flat", 50000) == 50000


# Every salary below comes out whole at the share it is awarded — 3120000 and
# 2600000 both divide exactly at 3% — so the uplift does not depend on how a
# fraction of a penny is treated.
def test_a_share_award_adds_its_share_of_the_salary():
    assert uplift_of(3120000, "share", 300) == 93600


def test_a_share_of_another_salary_that_divides_comes_out_whole():
    assert uplift_of(2600000, "share", 300) == 78000


def test_an_award_on_no_salary_adds_nothing():
    assert uplift_of(0, "share", 300) == 0


def test_an_award_of_nothing_adds_nothing():
    assert uplift_of(3120000, "share", 0) == 0


def test_a_new_salary_is_the_old_one_plus_the_uplift():
    assert new_salary(3120000, "share", 300) == 3213600


def test_a_flat_award_leaves_the_salary_higher_by_its_own_amount():
    assert new_salary(2600000, "flat", 50000) == 2650000


def test_a_run_of_awards_costs_what_they_add_between_them():
    assert cost_of([an_award(old_salary=3120000, new_salary=3213600),
                    an_award(id="b", old_salary=2600000, new_salary=2650000)]) == 143600


def test_no_awards_cost_nothing():
    assert cost_of([]) == 0


def test_the_average_share_is_the_cost_over_the_old_salaries():
    assert average_share([an_award(old_salary=3120000, new_salary=3213600)]) == 300


def test_awards_on_no_salary_average_nothing_rather_than_dividing_by_nothing():
    assert average_share([an_award(old_salary=0, new_salary=0)]) == 0


def test_the_bureau_lists_every_award():
    assert service().list(BUREAU, ListAwards())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_review():
    assert service().list(MANAGER, ListAwards(review_id="rv-1"))["total"] == 2


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListAwards(employee_id="ee-1"))["total"] == 1


def test_an_award_can_be_read():
    assert service().get(MANAGER, "aw-1").new_salary == 3213600


def test_an_award_nobody_made_is_missing():
    with pytest.raises(NotFound, match="award aw-9 was not found"):
        service().get(BUREAU, "aw-9")


def test_an_award_is_made_and_works_out_the_new_salary():
    row = service().make(MANAGER, MakeAward(
        review_id="rv-1", employee_id="ee-2", basis="share", amount=300,
        old_salary=2600000))
    assert row.new_salary == 2678000


def test_a_second_award_to_one_person_in_one_review_is_refused():
    with pytest.raises(Conflict, match="already has an award in that review"):
        service().make(MANAGER, MakeAward(
            review_id="rv-1", employee_id="ee-1", basis="flat", amount=1,
            old_salary=3120000))


def test_an_award_cannot_be_made_in_a_closed_review():
    with pytest.raises(Conflict, match="has been closed"):
        service().make(MANAGER, MakeAward(
            review_id="rv-2", employee_id="ee-2", basis="flat", amount=1,
            old_salary=2600000))


def test_a_basis_an_award_is_not_quoted_on_is_refused():
    with pytest.raises(Refused, match="is not a basis an award is quoted on"):
        service().make(MANAGER, MakeAward(
            review_id="rv-1", employee_id="ee-2", basis="guess", amount=1,
            old_salary=2600000))


def test_an_award_must_be_to_somebody_the_review_covers():
    with pytest.raises(Refused, match="somebody the review covers"):
        service().make(BUREAU, MakeAward(
            review_id="rv-1", employee_id="ee-4", basis="flat", amount=1,
            old_salary=2600000))


def test_what_a_review_costs_is_reported():
    answer = service().cost(MANAGER, "rv-1")
    assert answer["awards"] == 2 and answer["cost"] == 143600


def test_a_review_with_no_awards_costs_nothing():
    assert service().cost(MANAGER, "rv-2")["cost"] == 0


def client():
    return build_client(a_store())


def test_the_route_lists_awards():
    assert client().get("/awards", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_reports_what_a_review_costs():
    answer = client().get("/awards/cost/rv-1", headers=headers(MANAGER))
    assert answer.json()["cost"] == 143600


def test_the_route_makes_an_award_and_answers_201():
    answer = client().post("/awards", headers=headers(MANAGER), json={
        "review_id": "rv-1", "employee_id": "ee-2", "basis": "share",
        "amount": 300, "old_salary": 2600000})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_second_award_to_one_person():
    answer = client().post("/awards", headers=headers(MANAGER), json={
        "review_id": "rv-1", "employee_id": "ee-1", "basis": "flat",
        "amount": 1, "old_salary": 3120000})
    assert answer.status_code == 409
