"""Payments: the instructions that actually move the money."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_mandates, seed_payments,
)
from tare.common.types import PaymentInstruction, PayrollRun
from tare.modules.payments.rules import (
    failed_total, is_live, outstanding, outstanding_total, settled_total, sort_by_issue,
)
from tare.modules.payments.schemas import (
    FailPayment, IssuePayment, ListPayments, SettlePayment,
)
from tare.modules.payments.service import PaymentsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_mandates, seed_payments):
        seed(store)
    for run_id, employer_id, period in (("rn-1", "em-1", 1), ("rn-2", "em-1", 2),
                                        ("rn-3", "em-2", 1)):
        store.runs.insert(PayrollRun(
            id=run_id, employer_id=employer_id, calendar_id="pc-1", period=period,
            status="committed", opened_on="2025-05-06", committed_on="2025-05-07"))
    return store


def service():
    return PaymentsService(a_store())


def an_instruction(**kw) -> PaymentInstruction:
    base = dict(id="py-9", run_id="rn-1", employee_id="ee-1", employer_id="em-1",
                account="20-11-45/40028761", amount=221700, status="issued",
                issued_on="2025-05-28", settled_on=None)
    return PaymentInstruction(**{**base, **kw})


def test_instructions_read_earliest_first():
    rows = sort_by_issue([an_instruction(issued_on="2025-06-28"),
                          an_instruction(issued_on="2025-05-28")])
    assert [row.issued_on for row in rows] == ["2025-05-28", "2025-06-28"]


def test_an_issued_instruction_is_still_on_its_way():
    assert is_live(an_instruction(status="issued")) is True


def test_a_settled_instruction_has_arrived():
    assert is_live(an_instruction(status="settled")) is False


def test_a_cancelled_instruction_is_going_nowhere():
    assert is_live(an_instruction(status="cancelled")) is False


# Every instruction below is either on its way or has arrived, which is what an
# ordinary payment run holds; nothing here has come back, so what is still owed
# does not depend on how a payment the bank sent back is read.
def test_an_instruction_on_its_way_is_still_owed():
    assert [row.id for row in outstanding([an_instruction(id="a")])] == ["a"]


def test_an_instruction_that_arrived_is_no_longer_owed():
    assert outstanding([an_instruction(status="settled")]) == []


def test_a_cancelled_instruction_is_not_owed():
    assert outstanding([an_instruction(status="cancelled")]) == []


def test_what_is_still_owed_adds_the_live_instructions_up():
    rows = [an_instruction(id="a", amount=1000),
            an_instruction(id="b", amount=2000, status="settled")]
    assert outstanding_total(rows) == 1000


def test_what_has_arrived_adds_the_settled_instructions_up():
    rows = [an_instruction(id="a", amount=1000),
            an_instruction(id="b", amount=2000, status="settled")]
    assert settled_total(rows) == 2000


def test_nothing_has_arrived_when_everything_is_still_on_its_way():
    assert settled_total([an_instruction()]) == 0


def test_what_came_back_adds_the_failed_instructions_up():
    assert failed_total([an_instruction(amount=1000, status="failed")]) == 1000


def test_the_bureau_lists_every_instruction():
    assert service().list(BUREAU, ListPayments())["total"] == 3


def test_a_manager_lists_only_their_own_employers_instructions():
    assert service().list(MANAGER, ListPayments())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_run():
    assert service().list(MANAGER, ListPayments(run_id="rn-2"))["total"] == 1


def test_a_listing_can_be_narrowed_to_what_has_arrived():
    assert service().list(BUREAU, ListPayments(status="settled"))["total"] == 2


def test_an_instruction_can_be_read():
    assert service().get(MANAGER, "py-1").amount == 221700


def test_an_instruction_nobody_issued_is_missing():
    with pytest.raises(NotFound, match="payment py-9 was not found"):
        service().get(BUREAU, "py-9")


def test_a_manager_cannot_read_another_employers_instruction():
    with pytest.raises(Refused):
        service().get(MANAGER, "py-3")


def test_an_instruction_is_issued_into_the_standing_mandate():
    row = service().issue(MANAGER, IssuePayment(
        run_id="rn-2", employee_id="ee-2", amount=90000, issued_on="2025-08-28"))
    assert row.account == "30-22-10/11223344"


def test_a_second_instruction_for_one_person_on_one_run_is_refused():
    with pytest.raises(Conflict, match="already been paid for that run"):
        service().issue(MANAGER, IssuePayment(
            run_id="rn-2", employee_id="ee-1", amount=1000, issued_on="2025-08-28"))


def test_an_instruction_needs_a_mandate_to_pay_into():
    with pytest.raises(NotFound, match="mandate standing"):
        service().issue(MANAGER, IssuePayment(
            run_id="rn-2", employee_id="ee-3", amount=1000, issued_on="2025-08-28"))


def test_an_instruction_settles():
    answer = service().settle(MANAGER, "py-2", SettlePayment(settled_on="2025-06-30"))
    assert answer.status == "settled" and answer.settled_on == "2025-06-30"


def test_an_instruction_cannot_settle_twice():
    with pytest.raises(Conflict, match="already settled"):
        service().settle(MANAGER, "py-1", SettlePayment(settled_on="2025-06-30"))


def test_an_instruction_cannot_settle_before_it_was_issued():
    with pytest.raises(Refused, match="settle before it was issued"):
        service().settle(MANAGER, "py-2", SettlePayment(settled_on="2024-01-01"))


def test_an_instruction_that_comes_back_is_marked_failed():
    answer = service().fail(MANAGER, "py-2", FailPayment(reason="Account closed"))
    assert answer.status == "failed"


def test_an_instruction_that_has_arrived_cannot_come_back():
    with pytest.raises(Conflict, match="already settled"):
        service().fail(MANAGER, "py-1", FailPayment(reason="Too late"))


def test_an_instruction_is_cancelled():
    assert service().cancel(MANAGER, "py-2").status == "cancelled"


def test_a_cancelled_instruction_frees_the_person_to_be_paid_again():
    svc = service()
    svc.cancel(MANAGER, "py-2")
    assert svc.issue(MANAGER, IssuePayment(
        run_id="rn-2", employee_id="ee-1", amount=248555,
        issued_on="2025-06-28")).status == "issued"


def test_what_a_run_has_paid_and_still_owes_is_reported():
    answer = service().for_run(MANAGER, "rn-2")
    assert answer["outstanding"] == 248555 and answer["settled"] == 0


def test_a_run_that_has_paid_out_owes_nothing():
    assert service().for_run(MANAGER, "rn-1")["outstanding"] == 0


def client():
    return build_client(a_store())


def test_the_route_lists_instructions():
    assert client().get("/payments", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_what_a_run_has_paid():
    answer = client().get("/payments/run/rn-1", headers=headers(MANAGER))
    assert answer.json()["settled"] == 221700


def test_the_route_issues_an_instruction_and_answers_201():
    answer = client().post("/payments", headers=headers(MANAGER), json={
        "run_id": "rn-2", "employee_id": "ee-2", "amount": 90000,
        "issued_on": "2025-08-28"})
    assert answer.status_code == 201


def test_the_route_settles_an_instruction():
    answer = client().post("/payments/py-2/settle", headers=headers(MANAGER),
                           json={"settled_on": "2025-06-30"})
    assert answer.json()["status"] == "settled"
