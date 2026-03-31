"""The audit trail: who did what, and when."""

import pytest

from tare.common.errors import NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_audit, seed_employers,
)
from tare.common.types import AuditEntry
from tare.modules.audit.rules import actions_taken, between, by_operator, sort_by_happened
from tare.modules.audit.schemas import ListEntries, RecordEntry
from tare.modules.audit.service import AuditService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_audit):
        seed(store)
    return store


def service():
    return AuditService(a_store())


def an_entry(**kw) -> AuditEntry:
    base = dict(id="au-9", operator_id="op-1", operator_name="Rae", employer_id="em-1",
                action="committed run", subject="rn-1", happened_on="2025-05-07")
    return AuditEntry(**{**base, **kw})


def test_the_trail_reads_newest_first():
    rows = sort_by_happened([an_entry(id="a", happened_on="2025-05-07"),
                             an_entry(id="b", happened_on="2025-06-07")])
    assert [row.id for row in rows] == ["b", "a"]


def test_the_trail_can_be_narrowed_to_a_window():
    rows = between(a_store().audit.all(), "2025-06-01", "2025-06-30")
    assert [row.id for row in rows] == ["au-3"]


def test_the_trail_can_be_narrowed_to_one_operator():
    assert len(by_operator(a_store().audit.all(), "op-2")) == 2


def test_an_operator_who_did_nothing_has_no_entries():
    assert by_operator(a_store().audit.all(), "op-9") == []


def test_what_was_done_is_counted_by_kind():
    assert actions_taken(a_store().audit.all()) == {
        "committed run": 3, "published levy code": 1}


def test_an_empty_trail_counts_nothing():
    assert actions_taken([]) == {}


def test_the_bureau_reads_every_entry():
    assert service().list(BUREAU, ListEntries())["total"] == 4


def test_a_manager_reads_only_their_own_employers_entries():
    assert service().list(MANAGER, ListEntries())["total"] == 2


def test_a_listing_can_be_narrowed_to_an_action():
    assert service().list(BUREAU, ListEntries(action="committed run"))["total"] == 3


def test_a_listing_can_be_narrowed_to_an_operator():
    assert service().list(MANAGER, ListEntries(operator_id="op-2"))["total"] == 2


def test_an_entry_can_be_read():
    assert service().get(MANAGER, "au-2").subject == "rn-1"


def test_an_entry_nobody_wrote_is_missing():
    with pytest.raises(NotFound, match="audit entry au-9 was not found"):
        service().get(BUREAU, "au-9")


def test_a_manager_cannot_read_another_employers_entry():
    with pytest.raises(Refused):
        service().get(MANAGER, "au-4")


def test_an_entry_is_written_against_whoever_wrote_it():
    row = service().record(MANAGER, RecordEntry(
        employer_id="em-1", action="opened run", subject="rn-4",
        happened_on="2025-07-07"))
    assert row.operator_id == "op-2" and row.operator_name == "Sol"


def test_an_entry_can_be_written_against_no_employer():
    assert service().record(BUREAU, RecordEntry(
        action="published band", subject="A", happened_on="2025-07-07")).employer_id is None


def test_a_manager_cannot_write_against_another_employer():
    with pytest.raises(Refused):
        service().record(MANAGER, RecordEntry(
            employer_id="em-2", action="opened run", subject="rn-4",
            happened_on="2025-07-07"))


def client():
    return build_client(a_store())


def test_the_route_reads_the_trail():
    assert client().get("/audit", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_narrows_the_trail_for_a_manager():
    assert client().get("/audit", headers=headers(MANAGER)).json()["total"] == 2


def test_the_route_writes_an_entry_and_answers_201():
    answer = client().post("/audit", headers=headers(MANAGER), json={
        "employer_id": "em-1", "action": "opened run", "subject": "rn-4",
        "happened_on": "2025-07-07"})
    assert answer.status_code == 201


def test_the_route_answers_404_for_an_entry_nobody_wrote():
    assert client().get("/audit/au-9", headers=headers(BUREAU)).status_code == 404
