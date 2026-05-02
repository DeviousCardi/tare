"""Determinations: what a caught engagement is deemed to pay."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_determinations,
    seed_employers, seed_engagements,
)
from tare.common.types import Determination
from tare.modules.determinations.rules import (
    deemed_payment, running_allowance, sort_by_decided, total_deemed,
)
from tare.modules.determinations.schemas import DecideEngagement, ListDeterminations
from tare.modules.determinations.service import DeterminationsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_engagements, seed_determinations):
        seed(store)
    return store


def service():
    return DeterminationsService(a_store())


def a_determination(**kw) -> Determination:
    base = dict(id="dt-9", engagement_id="eg-1", employer_id="em-1", inside=True,
                fee=600000, allowable_expenses=20000, deemed_payment=550000,
                decided_on="2025-01-20")
    return Determination(**{**base, **kw})


def test_determinations_read_newest_first():
    rows = sort_by_decided([a_determination(id="a", decided_on="2025-01-20"),
                            a_determination(id="b", decided_on="2025-02-10")])
    assert [row.id for row in rows] == ["b", "a"]


# Both seeded fees come out whole at the running allowance — 5% of 600000 and
# of 400000 — so no fraction of a penny is left over and the answer does not
# depend on how one is treated.
def test_the_running_allowance_is_its_share_of_the_fee():
    assert running_allowance(600000) == 30000


def test_the_allowance_on_another_fee_that_divides_comes_out_whole():
    assert running_allowance(400000) == 20000


def test_no_fee_carries_no_allowance():
    assert running_allowance(0) == 0


def test_a_negative_fee_carries_no_allowance():
    assert running_allowance(-100) == 0


def test_the_deemed_payment_is_the_fee_less_the_allowance_and_the_expenses():
    assert deemed_payment(600000, 20000) == 550000


def test_a_fee_with_nothing_claimed_still_loses_the_allowance():
    assert deemed_payment(400000, 0) == 380000


def test_expenses_larger_than_the_fee_leave_nothing_deemed():
    assert deemed_payment(600000, 900000) == 0


def test_no_fee_is_deemed_to_pay_nothing():
    assert deemed_payment(0, 0) == 0


def test_what_is_deemed_across_a_run_counts_only_the_caught_ones():
    rows = [a_determination(id="a", inside=True, deemed_payment=550000),
            a_determination(id="b", inside=False, deemed_payment=0)]
    assert total_deemed(rows) == 550000


def test_a_run_with_nothing_caught_is_deemed_nothing():
    assert total_deemed([a_determination(inside=False, deemed_payment=0)]) == 0


def test_the_bureau_lists_every_determination():
    assert service().list(BUREAU, ListDeterminations())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_was_caught():
    assert service().list(MANAGER, ListDeterminations(inside_only=True))["total"] == 1


def test_a_listing_can_be_narrowed_to_an_engagement():
    assert service().list(MANAGER, ListDeterminations(engagement_id="eg-1"))["total"] == 1


def test_a_determination_can_be_read():
    assert service().get(MANAGER, "dt-1").deemed_payment == 550000


def test_a_determination_nobody_made_is_missing():
    with pytest.raises(NotFound, match="determination dt-9 was not found"):
        service().get(BUREAU, "dt-9")


def test_an_engagement_is_decided_and_the_deemed_payment_worked_out():
    # eg-3 belongs to the other employer, so it takes the bureau to decide it.
    row = service().decide(BUREAU, DecideEngagement(
        engagement_id="eg-3", inside=True, fee=600000, allowable_expenses=20000,
        decided_on="2025-03-01"))
    assert row.deemed_payment == 550000


def test_an_engagement_decided_outside_is_deemed_to_pay_nothing():
    row = service().decide(BUREAU, DecideEngagement(
        engagement_id="eg-3", inside=False, fee=600000, decided_on="2025-03-01"))
    assert row.deemed_payment == 0


def test_an_engagement_cannot_be_decided_twice():
    with pytest.raises(Conflict, match="already been decided"):
        service().decide(MANAGER, DecideEngagement(
            engagement_id="eg-1", inside=True, fee=1, decided_on="2025-03-01"))


def test_an_engagement_nobody_opened_cannot_be_decided():
    with pytest.raises(NotFound, match="engagement eg-9 was not found"):
        service().decide(BUREAU, DecideEngagement(
            engagement_id="eg-9", inside=True, fee=1, decided_on="2025-03-01"))


def test_what_an_employer_is_deemed_to_have_paid_is_reported():
    assert service().owed(MANAGER, "em-1") == 550000


def client():
    return build_client(a_store())


def test_the_route_lists_determinations():
    assert client().get("/determinations", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_reports_what_is_deemed():
    answer = client().get("/determinations/owed/em-1", headers=headers(MANAGER))
    assert answer.json()["deemed"] == 550000


def test_the_route_decides_an_engagement_and_answers_201():
    answer = client().post("/determinations", headers=headers(BUREAU), json={
        "engagement_id": "eg-3", "inside": True, "fee": 600000,
        "allowable_expenses": 20000, "decided_on": "2025-03-01"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_an_engagement_already_decided():
    answer = client().post("/determinations", headers=headers(MANAGER), json={
        "engagement_id": "eg-1", "inside": True, "fee": 1,
        "decided_on": "2025-03-01"})
    assert answer.status_code == 409
