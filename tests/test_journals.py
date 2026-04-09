"""Journals: what a payroll run posts to the nominal ledger."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_payslips,
)
from tare.common.types import JournalLine, Payslip, PayrollRun
from tare.modules.journals.rules import (
    NET_OWED, WAGES, balances, credits_of, debits_of, postings_for, sort_by_account,
)
from tare.modules.journals.schemas import ListJournal, PostRun
from tare.modules.journals.service import JournalsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_payslips):
        seed(store)
    for run_id, employer_id, period in (("rn-1", "em-1", 1), ("rn-2", "em-1", 2),
                                        ("rn-3", "em-2", 1)):
        store.runs.insert(PayrollRun(
            id=run_id, employer_id=employer_id, calendar_id="pc-1", period=period,
            status="committed", opened_on="2025-05-06", committed_on="2025-05-07"))
    return store


def service():
    return JournalsService(a_store())


def a_slip(**kw) -> Payslip:
    base = dict(id="ps-slip-9", run_id="rn-1", employee_id="ee-1", employer_id="em-1",
                period=1, start="2025-04-06", end="2025-05-05", gross=268000,
                taxable=268000, free_pay=108000, levy=32000, contributory=268000,
                contributions=12800, deductions=1500, net=221700)
    return Payslip(**{**base, **kw})


def a_line(**kw) -> JournalLine:
    base = dict(id="jl-9", run_id="rn-1", employer_id="em-1", account="5000",
                cost_centre_id=None, debit=268000, credit=0, narrative="Wages")
    return JournalLine(**{**base, **kw})


def test_lines_read_in_account_order():
    rows = sort_by_account([a_line(id="b", account="5000"),
                            a_line(id="a", account="2100")])
    assert [row.account for row in rows] == ["2100", "5000"]


def test_the_debits_are_added_up():
    assert debits_of([a_line(debit=268000), a_line(id="b", debit=1000)]) == 269000


def test_the_credits_are_added_up():
    assert credits_of([a_line(debit=0, credit=221700)]) == 221700


def test_a_posting_where_both_sides_match_balances():
    rows = [a_line(id="a", debit=268000, credit=0),
            a_line(id="b", debit=0, credit=268000)]
    assert balances(rows) is True


def test_a_posting_where_the_sides_do_not_match_does_not_balance():
    assert balances([a_line(debit=268000, credit=0)]) is False


def test_an_empty_posting_balances_trivially():
    assert balances([]) is True


# Every payslip below has its gross and its taxable figure the same, which is
# what an ordinary payslip carries, so the posting does not depend on which of
# the two the wages line is taken from.
def test_a_run_posts_a_line_for_each_account_it_touches():
    assert len(postings_for([a_slip()])) == 5


def test_the_wages_line_carries_the_whole_cost_as_a_debit():
    wages = [p for p in postings_for([a_slip()]) if p.account == WAGES][0]
    assert wages.debit == 268000 and wages.credit == 0


def test_the_net_owed_line_carries_what_is_left_as_a_credit():
    owed = [p for p in postings_for([a_slip()]) if p.account == NET_OWED][0]
    assert owed.credit == 221700 and owed.debit == 0


def test_a_posting_from_an_ordinary_payslip_balances():
    postings = postings_for([a_slip()])
    assert sum(p.debit for p in postings) == sum(p.credit for p in postings)


def test_two_payslips_post_one_line_for_each_account_between_them():
    assert len(postings_for([a_slip(id="a"), a_slip(id="b")])) == 5


def test_a_run_with_no_payslips_posts_lines_that_come_to_nothing():
    postings = postings_for([])
    assert sum(p.debit for p in postings) == 0


def test_a_run_is_posted():
    answer = service().post(MANAGER, PostRun(run_id="rn-1"))
    assert answer["balances"] is True and len(answer["lines"]) == 5


def test_a_posted_run_carries_the_wages_it_cost():
    answer = service().post(MANAGER, PostRun(run_id="rn-1"))
    assert answer["debits"] == 268000


def test_a_run_cannot_be_posted_twice():
    svc = service()
    svc.post(MANAGER, PostRun(run_id="rn-1"))
    with pytest.raises(Conflict, match="already been posted"):
        svc.post(MANAGER, PostRun(run_id="rn-1"))


def test_a_run_nobody_opened_cannot_be_posted():
    with pytest.raises(NotFound, match="run rn-99 was not found"):
        service().post(BUREAU, PostRun(run_id="rn-99"))


def test_a_manager_cannot_post_another_employers_run():
    with pytest.raises(Refused):
        service().post(MANAGER, PostRun(run_id="rn-3"))


def test_the_journal_for_a_run_is_read_back():
    svc = service()
    svc.post(MANAGER, PostRun(run_id="rn-1"))
    assert svc.of(MANAGER, "rn-1")["credits"] == 268000


def test_a_run_nobody_posted_has_an_empty_journal():
    assert service().of(MANAGER, "rn-2")["lines"] == []


def test_journal_lines_are_listed():
    svc = service()
    svc.post(MANAGER, PostRun(run_id="rn-1"))
    assert svc.list(MANAGER, ListJournal())["total"] == 5


def test_a_listing_can_be_narrowed_to_an_account():
    svc = service()
    svc.post(MANAGER, PostRun(run_id="rn-1"))
    assert svc.list(MANAGER, ListJournal(account=WAGES))["total"] == 1


def client():
    return build_client(a_store())


def test_the_route_posts_a_run_and_answers_201():
    answer = client().post("/journals", headers=headers(MANAGER), json={"run_id": "rn-1"})
    assert answer.status_code == 201 and answer.json()["balances"] is True


def test_the_route_reads_a_journal_back():
    cl = client()
    cl.post("/journals", headers=headers(MANAGER), json={"run_id": "rn-1"})
    assert cl.get("/journals/rn-1", headers=headers(MANAGER)).json()["debits"] == 268000


def test_the_route_answers_409_for_a_run_already_posted():
    cl = client()
    cl.post("/journals", headers=headers(MANAGER), json={"run_id": "rn-1"})
    assert cl.post("/journals", headers=headers(MANAGER),
                   json={"run_id": "rn-1"}).status_code == 409


def test_the_route_lists_journal_lines():
    cl = client()
    cl.post("/journals", headers=headers(MANAGER), json={"run_id": "rn-1"})
    assert cl.get("/journals", headers=headers(MANAGER)).json()["total"] == 5
