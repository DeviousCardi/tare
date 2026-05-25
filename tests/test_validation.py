"""Validation: what has to be right before a run can go ahead."""

import pytest

from tare.common.errors import NotFound
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_calendars, seed_contracts,
    seed_employees, seed_employers, seed_mandates,
)
from tare.common.types import PayrollRun
from tare.modules.validation.rules import (
    BLOCKING, WARNING, Finding, blocking, by_check, may_commit,
)
from tare.modules.validation.service import ValidationService


def a_store(with_contracts: bool = True, with_mandates: bool = True):
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_calendars):
        seed(store)
    if with_contracts:
        seed_contracts(store)
    if with_mandates:
        seed_mandates(store)
    store.runs.insert(PayrollRun(
        id="rn-1", employer_id="em-1", calendar_id="pc-1", period=2,
        status="draft", opened_on="2025-06-06", committed_on=None))
    return store


def a_finding(**kw) -> Finding:
    base = dict(check="contract", level=BLOCKING, subject="em-1/0001",
                detail="no terms")
    return Finding(**{**base, **kw})


def test_a_blocking_finding_blocks():
    assert a_finding(level=BLOCKING).blocks is True


def test_a_warning_does_not_block():
    assert a_finding(level=WARNING).blocks is False


def test_only_the_blocking_findings_survive_the_narrowing():
    rows = [a_finding(level=BLOCKING), a_finding(level=WARNING)]
    assert len(blocking(rows)) == 1


def test_a_run_with_nothing_blocking_may_go_ahead():
    assert may_commit([a_finding(level=WARNING)]) is True


def test_a_run_with_something_blocking_may_not():
    assert may_commit([a_finding(level=BLOCKING)]) is False


def test_a_run_with_no_findings_at_all_may_go_ahead():
    assert may_commit([]) is True


def test_findings_are_counted_by_check():
    rows = [a_finding(check="contract"), a_finding(check="mandate", level=WARNING)]
    assert by_check(rows) == {"contract": 1, "mandate": 1}


def test_a_run_where_everybody_has_terms_and_a_mandate_may_commit():
    assert ValidationService(a_store()).check(MANAGER, "rn-1")["may_commit"] is True


def test_somebody_without_terms_blocks_the_run():
    answer = ValidationService(a_store(with_contracts=False)).check(MANAGER, "rn-1")
    assert answer["may_commit"] is False and answer["blocking"] > 0


def test_somebody_without_terms_is_named_in_the_findings():
    answer = ValidationService(a_store(with_contracts=False)).check(MANAGER, "rn-1")
    assert any(row["check"] == "contract" for row in answer["findings"])


def test_somebody_without_a_mandate_is_only_a_warning():
    answer = ValidationService(a_store(with_mandates=False)).check(MANAGER, "rn-1")
    assert answer["may_commit"] is True and answer["findings"]


def test_the_blocking_findings_read_first():
    answer = ValidationService(a_store(with_contracts=False, with_mandates=False)).check(
        MANAGER, "rn-1")
    assert answer["findings"][0]["level"] == BLOCKING


def test_a_run_nobody_opened_cannot_be_checked():
    with pytest.raises(NotFound, match="run rn-9 was not found"):
        ValidationService(a_store()).check(BUREAU, "rn-9")


def test_the_findings_are_summarised_by_check():
    answer = ValidationService(a_store(with_contracts=False)).summary(MANAGER, "rn-1")
    assert "contract" in answer["by_check"]


def test_the_route_checks_a_run():
    client = build_client(a_store())
    assert client.get("/validation/rn-1", headers=headers(MANAGER)).json()["may_commit"] is True


def test_the_route_summarises_the_findings():
    client = build_client(a_store(with_contracts=False))
    answer = client.get("/validation/rn-1/summary", headers=headers(MANAGER))
    assert "contract" in answer.json()["by_check"]
