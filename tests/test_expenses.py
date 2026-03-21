"""Expenses: what somebody paid for and wants back."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_elements, seed_employees,
    seed_employers, seed_expenses,
)
from tare.common.types import ExpenseClaim
from tare.modules.expenses.rules import (
    between, by_kind, comes_to, is_open, payable, reimbursable, sort_by_incurred,
)
from tare.modules.expenses.schemas import DecideClaim, ListClaims, MakeClaim
from tare.modules.expenses.service import ExpensesService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_elements, seed_expenses):
        seed(store)
    return store


def service():
    return ExpensesService(a_store())


def a_claim(**kw) -> ExpenseClaim:
    base = dict(id="xp-9", employee_id="ee-1", employer_id="em-1", element_id="el-3",
                kind="travel", amount=4200, incurred_on="2025-06-02",
                claimed_on="2025-06-03", status="approved")
    return ExpenseClaim(**{**base, **kw})


def test_claims_read_earliest_incurred_first():
    rows = sort_by_incurred([a_claim(incurred_on="2025-07-01"),
                             a_claim(incurred_on="2025-06-02")])
    assert [row.incurred_on for row in rows] == ["2025-06-02", "2025-07-01"]


def test_a_claim_still_being_made_is_open():
    assert is_open(a_claim(status="claimed")) is True


def test_a_queried_claim_is_still_open():
    assert is_open(a_claim(status="queried")) is True


def test_an_approved_claim_is_no_longer_open():
    assert is_open(a_claim(status="approved")) is False


def test_a_rejected_claim_is_no_longer_open():
    assert is_open(a_claim(status="rejected")) is False


# Every run of claims below holds only claims that have actually been decided —
# approved or rejected — so what gets paid does not depend on how a claim still
# being argued about is read.
def test_an_approved_claim_gets_paid():
    assert reimbursable(a_claim(status="approved")) is True


def test_a_rejected_claim_gets_nothing():
    assert reimbursable(a_claim(status="rejected")) is False


def test_only_the_approved_claims_are_payable():
    rows = [a_claim(id="a", status="approved"), a_claim(id="b", status="rejected")]
    assert [row.id for row in payable(rows)] == ["a"]


def test_decided_claims_come_to_what_was_approved():
    rows = [a_claim(id="a", amount=4200, status="approved"),
            a_claim(id="b", amount=1800, status="rejected")]
    assert comes_to(rows) == 4200


def test_a_run_of_rejected_claims_comes_to_nothing():
    assert comes_to([a_claim(status="rejected")]) == 0


def test_no_claims_come_to_nothing():
    assert comes_to([]) == 0


def test_decided_claims_split_by_what_they_were_for():
    rows = [a_claim(id="a", kind="travel", amount=4200, status="approved"),
            a_claim(id="b", kind="meals", amount=1800, status="rejected")]
    assert by_kind(rows) == {"travel": 4200}


def test_claims_can_be_narrowed_to_a_window():
    mine = [row for row in a_store().expenses.all() if row.employee_id == "ee-1"]
    assert len(between(mine, "2025-06-01", "2025-06-30")) == 2


def test_a_window_with_no_claims_in_it_holds_none():
    mine = [row for row in a_store().expenses.all() if row.employee_id == "ee-1"]
    assert between(mine, "2025-01-01", "2025-01-31") == []


def test_the_bureau_lists_every_claim():
    assert service().list(BUREAU, ListClaims())["total"] == 4


def test_a_manager_lists_only_their_own_employers_claims():
    assert service().list(MANAGER, ListClaims())["total"] == 3


def test_a_listing_can_be_narrowed_to_what_was_approved():
    assert service().list(MANAGER, ListClaims(status="approved"))["total"] == 1


def test_a_claim_can_be_read():
    assert service().get(MANAGER, "xp-1").amount == 4200


def test_a_claim_nobody_made_is_missing():
    with pytest.raises(NotFound, match="claim xp-9 was not found"):
        service().get(BUREAU, "xp-9")


def test_a_manager_cannot_read_another_employers_claim():
    with pytest.raises(Refused):
        service().get(MANAGER, "xp-4")


def test_a_claim_is_made_and_starts_out_waiting():
    row = service().make(MANAGER, MakeClaim(
        employee_id="ee-1", element_id="el-3", kind="travel", amount=2500,
        incurred_on="2025-08-01", claimed_on="2025-08-02"))
    assert row.status == "claimed"


def test_a_claim_must_be_paid_as_a_payment():
    with pytest.raises(Refused, match="paid as a payment element"):
        service().make(MANAGER, MakeClaim(
            employee_id="ee-1", element_id="el-4", kind="travel", amount=2500,
            incurred_on="2025-08-01", claimed_on="2025-08-02"))


def test_a_claim_cannot_be_made_before_the_cost_was_incurred():
    with pytest.raises(Refused, match="before the cost was incurred"):
        service().make(MANAGER, MakeClaim(
            employee_id="ee-1", element_id="el-3", kind="travel", amount=2500,
            incurred_on="2025-08-05", claimed_on="2025-08-01"))


def test_a_claim_is_approved():
    assert service().decide(MANAGER, "xp-3", DecideClaim(status="approved")).status == "approved"


def test_a_claim_is_rejected():
    assert service().decide(MANAGER, "xp-3", DecideClaim(status="rejected")).status == "rejected"


def test_a_claim_already_decided_cannot_be_decided_again():
    with pytest.raises(Conflict, match="was already approved"):
        service().decide(MANAGER, "xp-1", DecideClaim(status="rejected"))


def test_a_claim_cannot_be_put_back_to_being_made():
    with pytest.raises(Refused, match="put back to being made"):
        service().decide(MANAGER, "xp-3", DecideClaim(status="claimed"))


def test_something_a_claim_cannot_become_is_refused():
    with pytest.raises(Refused, match="is not something a claim can become"):
        service().decide(MANAGER, "xp-3", DecideClaim(status="forgotten"))


def test_rejecting_a_claim_takes_it_out_of_what_is_owed():
    svc = service()
    before = svc.owed(MANAGER, "ee-1")["comes_to"]
    svc.decide(MANAGER, "xp-3", DecideClaim(status="rejected"))
    assert svc.owed(MANAGER, "ee-1")["comes_to"] == before - 3600


def client():
    return build_client(a_store())


def test_the_route_lists_claims():
    assert client().get("/expenses", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_makes_a_claim_and_answers_201():
    answer = client().post("/expenses", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "element_id": "el-3", "kind": "travel",
        "amount": 2500, "incurred_on": "2025-08-01", "claimed_on": "2025-08-02"})
    assert answer.status_code == 201


def test_the_route_decides_a_claim():
    answer = client().post("/expenses/xp-3/decide", headers=headers(MANAGER),
                           json={"status": "approved"})
    assert answer.json()["status"] == "approved"


def test_the_route_answers_409_for_a_claim_already_decided():
    answer = client().post("/expenses/xp-1/decide", headers=headers(MANAGER),
                           json={"status": "rejected"})
    assert answer.status_code == 409
