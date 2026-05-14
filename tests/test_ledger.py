"""The ledger: what the nominal accounts come to."""

import pytest

from tare.common.errors import Refused
from tare.common.testing import BUREAU, MANAGER, build_client, build_store, headers, seed_employers
from tare.common.types import JournalLine
from tare.modules.ledger.rules import balance_of, balances_of, trial_balance
from tare.modules.ledger.service import LedgerService


def a_line(**kw) -> JournalLine:
    base = dict(id="jl-9", run_id="rn-1", employer_id="em-1", account="5000",
                cost_centre_id=None, debit=268000, credit=0, narrative="Wages")
    return JournalLine(**{**base, **kw})


def a_store():
    store = build_store()
    seed_employers(store)
    for row in (a_line(id="jl-1", account="5000", debit=268000, credit=0),
                a_line(id="jl-2", account="2100", debit=0, credit=221700),
                a_line(id="jl-3", account="2210", debit=0, credit=32000),
                a_line(id="jl-4", account="2220", debit=0, credit=12800),
                a_line(id="jl-5", account="2230", debit=0, credit=1500)):
        store.journals.insert(row)
    return store


def service():
    return LedgerService(a_store())


def test_one_balance_comes_back_for_each_account():
    assert len(balances_of(a_store().journals.all())) == 5


def test_balances_read_in_account_order():
    accounts = [row.account for row in balances_of(a_store().journals.all())]
    assert accounts == sorted(accounts)


def test_a_debit_account_stands_above_nothing():
    assert balance_of(a_store().journals.all(), "5000").balance == 268000


def test_a_credit_account_stands_below_nothing():
    assert balance_of(a_store().journals.all(), "2100").balance == -221700


def test_two_lines_on_one_account_add_together():
    rows = [a_line(id="a", account="5000", debit=1000, credit=0),
            a_line(id="b", account="5000", debit=500, credit=0)]
    assert balance_of(rows, "5000").debits == 1500


def test_an_account_nobody_posted_to_stands_at_nothing():
    assert balance_of(a_store().journals.all(), "9999").balance == 0


def test_a_ledger_whose_sides_match_comes_back_to_nothing():
    assert trial_balance(a_store().journals.all()) is True


def test_a_ledger_missing_a_side_does_not_come_back_to_nothing():
    assert trial_balance([a_line(debit=1000, credit=0)]) is False


def test_an_empty_ledger_comes_back_to_nothing():
    assert trial_balance([]) is True


def test_the_ledger_for_an_employer_is_reported():
    answer = service().of(MANAGER, "em-1")
    assert answer["balances"] is True and len(answer["accounts"]) == 5


def test_an_employer_with_nothing_posted_has_an_empty_ledger():
    assert service().of(BUREAU, "em-2")["accounts"] == []


def test_a_manager_cannot_read_another_employers_ledger():
    with pytest.raises(Refused):
        service().of(MANAGER, "em-2")


def test_one_account_is_reported_on_its_own():
    assert service().account(MANAGER, "em-1", "5000")["balance"] == 268000


def client():
    return build_client(a_store())


def test_the_route_reports_a_ledger():
    answer = client().get("/ledger/em-1", headers=headers(MANAGER))
    assert answer.json()["balances"] is True


def test_the_route_reports_one_account():
    answer = client().get("/ledger/em-1/account/2100", headers=headers(MANAGER))
    assert answer.json()["balance"] == -221700
