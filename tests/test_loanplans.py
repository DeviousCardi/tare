"""Loan plans: graduate contributions repaid through the payroll."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_loan_plans,
)
from tare.common.types import LoanPlan
from tare.modules.loanplans.rules import (
    above_threshold, due_now, live_plans, remaining, settled, sort_by_started,
)
from tare.modules.loanplans.schemas import (
    CollectOnPlan, ListPlans, SettlePlan, StartPlan,
)
from tare.modules.loanplans.service import LoanPlansService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_loan_plans):
        seed(store)
    return store


def service():
    return LoanPlansService(a_store())


def a_plan(**kw) -> LoanPlan:
    base = dict(id="lp-9", employee_id="ee-1", employer_id="em-1",
                reference="GC/2019/0009", plan_type="two", total=1800000,
                collected=420000, period_threshold=180000, rate_basis_points=900,
                started_on="2022-04-06", settled_on=None)
    return LoanPlan(**{**base, **kw})


def test_plans_read_earliest_first():
    rows = sort_by_started([a_plan(started_on="2022-04-06"), a_plan(started_on="2021-04-06")])
    assert [row.started_on for row in rows] == ["2021-04-06", "2022-04-06"]


def test_a_plan_repaid_in_full_is_settled():
    assert settled(a_plan(total=900000, collected=900000)) is True


def test_a_plan_part_way_through_is_not_settled():
    assert settled(a_plan(total=1800000, collected=420000)) is False


def test_a_plan_marked_settled_is_settled():
    assert settled(a_plan(settled_on="2025-03-31")) is True


def test_what_is_left_is_the_total_less_what_was_collected():
    assert remaining(a_plan(total=1800000, collected=420000)) == 1380000


def test_a_plan_repaid_in_full_has_nothing_left():
    assert remaining(a_plan(total=900000, collected=900000)) == 0


def test_only_the_pay_above_the_threshold_is_worked_on():
    assert above_threshold(a_plan(period_threshold=180000), 275299) == 95299


def test_pay_below_the_threshold_leaves_nothing_to_work_on():
    assert above_threshold(a_plan(period_threshold=180000), 150000) == 0


# Every plan below is either still owing with nothing marked settled, or has
# been repaid in full — which is what an ordinary plan looks like — so what
# comes out does not depend on how a plan settled while still owing is read.
def test_a_share_of_the_pay_above_the_threshold_comes_out():
    assert due_now(a_plan(total=1800000, collected=420000), 275299) == 8577


def test_pay_below_the_threshold_takes_nothing():
    assert due_now(a_plan(), 150000) == 0


def test_no_pay_takes_nothing():
    assert due_now(a_plan(), 0) == 0


def test_a_plan_repaid_in_full_takes_nothing_more():
    assert due_now(a_plan(total=900000, collected=900000), 275299) == 0


def test_a_plan_takes_no_more_than_it_is_still_owed():
    assert due_now(a_plan(total=900000, collected=899000), 275299) == 1000


def test_the_live_plans_for_somebody_are_found():
    assert [row.id for row in live_plans(a_store().loan_plans.all(), "ee-1")] == ["lp-1"]


def test_somebody_whose_plan_is_settled_has_none_live():
    assert live_plans(a_store().loan_plans.all(), "ee-2") == []


def test_the_bureau_lists_every_plan():
    assert service().list(BUREAU, ListPlans())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_still_live():
    assert service().list(MANAGER, ListPlans(live_only=True))["total"] == 1


def test_a_plan_can_be_read():
    assert service().get(MANAGER, "lp-1").reference == "GC/2019/0001"


def test_a_plan_nobody_started_is_missing():
    with pytest.raises(NotFound, match="loan plan lp-9 was not found"):
        service().get(BUREAU, "lp-9")


def test_a_plan_is_started():
    row = service().start(MANAGER, StartPlan(
        employee_id="ee-3", reference="GC/2020/0003", plan_type="one",
        total=600000, period_threshold=160000, rate_basis_points=900,
        started_on="2023-04-06"))
    assert row.collected == 0


def test_a_plan_the_revenue_does_not_publish_is_refused():
    with pytest.raises(Refused, match="is not a plan the Revenue publishes"):
        service().start(MANAGER, StartPlan(
            employee_id="ee-3", reference="GC/2020/0003", plan_type="nine",
            total=600000, period_threshold=160000, rate_basis_points=900,
            started_on="2023-04-06"))


def test_a_reference_already_started_is_refused():
    with pytest.raises(Conflict, match="already been started"):
        service().start(MANAGER, StartPlan(
            employee_id="ee-3", reference="GC/2019/0001", plan_type="one",
            total=600000, period_threshold=160000, rate_basis_points=900,
            started_on="2023-04-06"))


def test_something_is_collected_against_a_plan():
    assert service().collect(MANAGER, "lp-1", CollectOnPlan(amount=8577)).collected == 428577


def test_a_plan_cannot_collect_more_than_it_is_owed():
    with pytest.raises(Refused, match="more than it is still owed"):
        service().collect(MANAGER, "lp-1", CollectOnPlan(amount=2000000))


def test_a_settled_plan_cannot_collect_again():
    with pytest.raises(Conflict, match="already settled"):
        service().collect(MANAGER, "lp-2", CollectOnPlan(amount=1000))


def test_a_plan_is_settled():
    assert service().settle(MANAGER, "lp-1", SettlePlan(settled_on="2025-09-30")).settled_on == "2025-09-30"


def test_a_plan_cannot_be_settled_twice():
    with pytest.raises(Conflict, match="already been settled"):
        service().settle(MANAGER, "lp-2", SettlePlan(settled_on="2025-09-30"))


def test_a_plan_cannot_settle_before_it_started():
    with pytest.raises(Refused, match="settle before it started"):
        service().settle(MANAGER, "lp-1", SettlePlan(settled_on="2019-01-01"))


def test_what_comes_out_of_a_period_is_reported():
    answer = service().due(MANAGER, "lp-1", 275299)
    assert answer["above_threshold"] == 95299 and answer["due"] == 8577


def test_negative_pay_is_refused():
    with pytest.raises(Refused, match="pay cannot be negative"):
        service().due(MANAGER, "lp-1", -1)


def client():
    return build_client(a_store())


def test_the_route_lists_plans():
    assert client().get("/loan-plans", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_reports_what_comes_out():
    answer = client().get("/loan-plans/lp-1/due?pay=275299", headers=headers(MANAGER))
    assert answer.json()["due"] == 8577


def test_the_route_starts_a_plan_and_answers_201():
    answer = client().post("/loan-plans", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "reference": "GC/2020/0003", "plan_type": "one",
        "total": 600000, "period_threshold": 160000, "rate_basis_points": 900,
        "started_on": "2023-04-06"})
    assert answer.status_code == 201


def test_the_route_collects_against_a_plan():
    answer = client().post("/loan-plans/lp-1/collect", headers=headers(MANAGER),
                           json={"amount": 8577})
    assert answer.json()["collected"] == 428577
