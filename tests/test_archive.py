"""The archive: the runs put beyond further change."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_archive, seed_employees,
    seed_employers, seed_payslips,
)
from tare.common.types import ArchiveEntry, PayrollRun
from tare.modules.archive.rules import between, holds, sort_by_closed, totals_of
from tare.modules.archive.schemas import CloseOffRun, ListArchive
from tare.modules.archive.service import ArchiveService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_payslips, seed_archive):
        seed(store)
    for run_id, employer_id, period in (("rn-1", "em-1", 1), ("rn-2", "em-1", 2),
                                        ("rn-3", "em-2", 1)):
        store.runs.insert(PayrollRun(
            id=run_id, employer_id=employer_id, calendar_id="pc-1", period=period,
            status="committed", opened_on="2025-05-06", committed_on="2025-05-07"))
    return store


def service():
    return ArchiveService(a_store())


def an_entry(**kw) -> ArchiveEntry:
    base = dict(id="ar-9", employer_id="em-1", run_id="rn-1", closed_on="2025-06-30",
                payslips=1, net=221700)
    return ArchiveEntry(**{**base, **kw})


def test_the_archive_reads_newest_first():
    rows = sort_by_closed([an_entry(id="a", closed_on="2025-05-30"),
                           an_entry(id="b", closed_on="2025-06-30")])
    assert [row.id for row in rows] == ["b", "a"]


def test_the_archive_can_be_narrowed_to_a_window():
    assert len(between(a_store().archive.all(), "2025-06-01", "2025-06-30")) == 2


def test_a_window_with_nothing_closed_off_in_it_holds_none():
    assert between(a_store().archive.all(), "2025-01-01", "2025-01-31") == []


def test_the_archive_knows_which_runs_it_holds():
    assert holds(a_store().archive.all(), "rn-1") is True


def test_the_archive_does_not_hold_a_run_nobody_closed_off():
    assert holds(a_store().archive.all(), "rn-2") is False


def test_the_archive_totals_what_it_holds():
    assert totals_of(a_store().archive.all()) == {
        "runs": 2, "payslips": 2, "net": 501540}


def test_an_empty_archive_totals_nothing():
    assert totals_of([]) == {"runs": 0, "payslips": 0, "net": 0}


def test_the_bureau_lists_everything_closed_off():
    assert service().list(BUREAU, ListArchive())["total"] == 2


def test_a_manager_lists_only_their_own_employers():
    assert service().list(MANAGER, ListArchive())["total"] == 1


def test_an_entry_can_be_read():
    assert service().get(MANAGER, "ar-1").net == 221700


def test_an_entry_nobody_wrote_is_missing():
    with pytest.raises(NotFound, match="archive entry ar-9 was not found"):
        service().get(BUREAU, "ar-9")


def test_a_manager_cannot_read_another_employers_entry():
    with pytest.raises(Refused):
        service().get(MANAGER, "ar-2")


def test_the_bureau_closes_a_run_off():
    row = service().close_off(BUREAU, CloseOffRun(run_id="rn-2", closed_on="2025-07-31"))
    assert row.payslips == 1 and row.net == 248555


def test_nobody_but_the_bureau_closes_a_run_off():
    with pytest.raises(Refused, match="only the bureau may close a run off"):
        service().close_off(MANAGER, CloseOffRun(run_id="rn-2", closed_on="2025-07-31"))


def test_a_run_already_closed_off_cannot_be_closed_again():
    with pytest.raises(Conflict, match="already been closed off"):
        service().close_off(BUREAU, CloseOffRun(run_id="rn-1", closed_on="2025-07-31"))


def test_a_run_cannot_be_closed_off_before_it_was_committed():
    with pytest.raises(Refused, match="before it was committed"):
        service().close_off(BUREAU, CloseOffRun(run_id="rn-2", closed_on="2024-01-01"))


def test_closing_a_run_off_puts_it_in_the_archive():
    svc = service()
    svc.close_off(BUREAU, CloseOffRun(run_id="rn-2", closed_on="2025-07-31"))
    assert svc.holds(BUREAU, "rn-2") is True


def test_the_archive_totals_are_reported():
    assert service().totals(BUREAU)["net"] == 501540


def client():
    return build_client(a_store())


def test_the_route_lists_the_archive():
    assert client().get("/archive", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_reports_the_totals():
    assert client().get("/archive/totals", headers=headers(BUREAU)).json()["runs"] == 2


def test_the_route_says_whether_a_run_is_closed_off():
    answer = client().get("/archive/holds/rn-1", headers=headers(MANAGER))
    assert answer.json()["closed_off"] is True


def test_the_route_closes_a_run_off_and_answers_201():
    answer = client().post("/archive", headers=headers(BUREAU),
                           json={"run_id": "rn-2", "closed_on": "2025-07-31"})
    assert answer.status_code == 201
