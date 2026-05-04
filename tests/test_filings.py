"""Filings: the returns the bureau owes the Revenue."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_filings,
)
from tare.common.types import Filing, PayrollRun
from tare.modules.filings.rules import (
    days_to_go, due_on_for, is_late, owed_by, sort_by_period,
)
from tare.modules.filings.schemas import ListFilings, RaiseFiling
from tare.modules.filings.service import FilingsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_filings):
        seed(store)
    for run_id, employer_id, period in (("rn-1", "em-1", 1), ("rn-2", "em-1", 2),
                                        ("rn-3", "em-2", 1), ("rn-4", "em-1", 3)):
        store.runs.insert(PayrollRun(
            id=run_id, employer_id=employer_id, calendar_id="pc-1", period=period,
            status="committed", opened_on="2025-05-06", committed_on="2025-05-07"))
    return store


def service():
    return FilingsService(a_store())


def a_filing(**kw) -> Filing:
    base = dict(id="fl-9", employer_id="em-1", run_id="rn-1", period=1,
                period_end="2025-05-05", due_on="2025-05-19", gross=268000,
                levy=32000, contributions=12800)
    return Filing(**{**base, **kw})


def test_filings_read_by_period():
    rows = sort_by_period([a_filing(period=2), a_filing(period=1)])
    assert [row.period for row in rows] == [1, 2]


def test_a_return_falls_due_after_the_period_it_covers():
    assert due_on_for("2025-05-05") == "2025-05-19"


def test_what_a_return_owes_takes_in_the_levy_and_contributions():
    assert owed_by(a_filing(levy=32000, contributions=12800)) == 44800


def test_a_return_owing_nothing_owes_nothing():
    assert owed_by(a_filing(levy=0, contributions=0)) == 0


# Every day below sits either on or before the day the period ends, or well
# after the day the return falls due, so whether it is late does not depend on
# which of the two days it is measured against.
def test_a_return_is_not_late_on_the_day_its_period_ends():
    assert is_late(a_filing(period_end="2025-05-05"), "2025-05-05") is False


def test_a_return_is_not_late_before_its_period_ends():
    assert is_late(a_filing(period_end="2025-05-05"), "2025-05-01") is False


def test_a_return_is_late_well_past_the_day_it_fell_due():
    assert is_late(a_filing(due_on="2025-05-19"), "2025-06-30") is True


def test_the_days_left_count_both_ends():
    assert days_to_go(a_filing(due_on="2025-05-19"), "2025-05-17") == 3


def test_nothing_is_left_once_the_day_is_past():
    assert days_to_go(a_filing(due_on="2025-05-19"), "2025-06-01") == 0


def test_the_bureau_lists_every_filing():
    assert service().list(BUREAU, ListFilings())["total"] == 3


def test_a_manager_lists_only_their_own_employers_filings():
    assert service().list(MANAGER, ListFilings())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_period():
    assert service().list(BUREAU, ListFilings(period=1))["total"] == 2


def test_a_filing_can_be_read():
    assert service().get(MANAGER, "fl-1").gross == 268000


def test_a_filing_nobody_raised_is_missing():
    with pytest.raises(NotFound, match="filing fl-9 was not found"):
        service().get(BUREAU, "fl-9")


def test_a_manager_cannot_read_another_employers_filing():
    with pytest.raises(Refused):
        service().get(MANAGER, "fl-3")


def test_a_filing_is_raised_and_works_out_when_it_is_due():
    row = service().raise_it(MANAGER, RaiseFiling(
        run_id="rn-4", period=3, period_end="2025-07-05", gross=1, levy=1,
        contributions=1))
    assert row.due_on == "2025-07-19"


def test_a_run_already_filed_cannot_be_filed_again():
    with pytest.raises(Conflict, match="already been filed"):
        service().raise_it(MANAGER, RaiseFiling(
            run_id="rn-1", period=1, period_end="2025-05-05", gross=1, levy=1,
            contributions=1))


def test_the_state_of_a_filing_is_reported():
    answer = service().state(MANAGER, "fl-1", "2025-05-17")
    assert answer["owed"] == 44800 and answer["days_to_go"] == 3


def client():
    return build_client(a_store())


def test_the_route_lists_filings():
    assert client().get("/filings", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_the_state_of_a_filing():
    answer = client().get("/filings/fl-1/state?on=2025-05-17", headers=headers(MANAGER))
    assert answer.json()["owed"] == 44800


def test_the_route_raises_a_filing_and_answers_201():
    answer = client().post("/filings", headers=headers(MANAGER), json={
        "run_id": "rn-4", "period": 3, "period_end": "2025-07-05", "gross": 1,
        "levy": 1, "contributions": 1})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_run_already_filed():
    answer = client().post("/filings", headers=headers(MANAGER), json={
        "run_id": "rn-1", "period": 1, "period_end": "2025-05-05", "gross": 1,
        "levy": 1, "contributions": 1})
    assert answer.status_code == 409
