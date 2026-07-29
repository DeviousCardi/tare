"""Remittances: what the bureau owes each provider for a run."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_providers,
    seed_remittances,
)
from tare.common.types import PayrollRun, Remittance
from tare.modules.remittances.rules import (
    days_to_go, due_on_for, is_overdue, is_waiting, owed_to, sort_by_due,
    waiting,
)
from tare.modules.remittances.schemas import (
    ListRemittances, RaiseRemittance, SendRemittance,
)
from tare.modules.remittances.service import RemittancesService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_providers, seed_remittances):
        seed(store)
    for run_id, employer_id, period in (("rn-1", "em-1", 1), ("rn-2", "em-1", 2),
                                        ("rn-3", "em-2", 1)):
        store.runs.insert(PayrollRun(
            id=run_id, employer_id=employer_id, calendar_id="pc-1", period=period,
            status="committed", opened_on="2025-05-06", committed_on="2025-05-07"))
    return store


def service():
    return RemittancesService(a_store())


def a_remittance(**kw) -> Remittance:
    base = dict(id="rm-9", run_id="rn-1", employer_id="em-1", provider_id="pv-1",
                amount=44800, due_on="2025-05-26", sent_on=None)
    return Remittance(**{**base, **kw})


def test_remittances_read_by_the_day_they_are_due():
    rows = sort_by_due([a_remittance(due_on="2025-06-26"),
                        a_remittance(due_on="2025-05-26")])
    assert [row.due_on for row in rows] == ["2025-05-26", "2025-06-26"]


def test_the_day_a_run_is_due_follows_the_day_it_was_committed():
    assert due_on_for("2025-05-07") == "2025-05-26"


def test_a_remittance_nobody_has_sent_is_waiting():
    assert is_waiting(a_remittance(sent_on=None)) is True


def test_a_remittance_that_has_gone_is_not_waiting():
    assert is_waiting(a_remittance(sent_on="2025-05-20")) is False


def test_only_the_waiting_remittances_survive_the_narrowing():
    rows = waiting([a_remittance(id="a"), a_remittance(id="b", sent_on="2025-05-20")])
    assert [row.id for row in rows] == ["a"]


def test_a_remittance_past_its_day_is_overdue():
    assert is_overdue(a_remittance(due_on="2025-05-26"), "2025-06-01") is True


def test_a_remittance_on_its_day_is_not_yet_overdue():
    assert is_overdue(a_remittance(due_on="2025-05-26"), "2025-05-26") is False


def test_a_remittance_that_has_gone_is_never_overdue():
    assert is_overdue(a_remittance(due_on="2025-05-26", sent_on="2025-05-20"),
                      "2025-06-01") is False


def test_the_days_left_count_both_ends():
    assert days_to_go(a_remittance(due_on="2025-05-26"), "2025-05-24") == 3


def test_nothing_is_left_once_the_day_is_past():
    assert days_to_go(a_remittance(due_on="2025-05-26"), "2025-06-01") == 0


def test_what_is_owed_to_a_provider_adds_the_waiting_ones_up():
    assert owed_to(a_store().remittances.all(), "pv-1") == 92070


def test_a_provider_owed_nothing_is_owed_nothing():
    assert owed_to(a_store().remittances.all(), "pv-3") == 0


def test_the_bureau_lists_every_remittance():
    assert service().list(BUREAU, ListRemittances())["total"] == 4


def test_a_manager_lists_only_their_own_employers_remittances():
    assert service().list(MANAGER, ListRemittances())["total"] == 3


def test_a_listing_can_be_narrowed_to_what_is_still_waiting():
    assert service().list(MANAGER, ListRemittances(waiting_only=True))["total"] == 2


def test_a_listing_can_be_narrowed_to_a_provider():
    assert service().list(MANAGER, ListRemittances(provider_id="pv-2"))["total"] == 1


def test_a_remittance_can_be_read():
    assert service().get(MANAGER, "rm-1").amount == 44800


def test_a_remittance_nobody_raised_is_missing():
    with pytest.raises(NotFound, match="remittance rm-9 was not found"):
        service().get(BUREAU, "rm-9")


def test_a_manager_cannot_read_another_employers_remittance():
    with pytest.raises(Refused):
        service().get(MANAGER, "rm-4")


def test_a_remittance_is_raised():
    row = service().raise_it(MANAGER, RaiseRemittance(
        run_id="rn-2", provider_id="pv-2", amount=1500, due_on="2025-06-26"))
    assert row.sent_on is None


def test_a_second_remittance_to_one_provider_on_one_run_is_refused():
    with pytest.raises(Conflict, match="already been raised for that run"):
        service().raise_it(MANAGER, RaiseRemittance(
            run_id="rn-1", provider_id="pv-1", amount=1, due_on="2025-05-26"))


def test_a_remittance_goes():
    assert service() \
        .send(MANAGER, "rm-2", SendRemittance(sent_on="2025-06-20")).sent_on == "2025-06-20"


def test_a_remittance_cannot_go_twice():
    with pytest.raises(Conflict, match="already gone"):
        service().send(MANAGER, "rm-1", SendRemittance(sent_on="2025-06-20"))


def test_the_overdue_remittances_are_reported():
    assert [row.id for row in service().overdue(MANAGER, "2025-06-01")] == ["rm-3"]


def test_nothing_is_overdue_before_anything_falls_due():
    assert service().overdue(MANAGER, "2025-05-01") == []


def test_what_is_owed_to_a_provider_is_reported():
    assert service().owed(MANAGER, "pv-1") == 25244


def client():
    return build_client(a_store())


def test_the_route_lists_remittances():
    assert client().get("/remittances", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reports_what_is_overdue():
    answer = client().get("/remittances/overdue?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["total"] == 1


def test_the_route_raises_a_remittance_and_answers_201():
    answer = client().post("/remittances", headers=headers(MANAGER), json={
        "run_id": "rn-2", "provider_id": "pv-2", "amount": 1500,
        "due_on": "2025-06-26"})
    assert answer.status_code == 201


def test_the_route_sends_a_remittance():
    answer = client().post("/remittances/rm-2/send", headers=headers(MANAGER),
                           json={"sent_on": "2025-06-20"})
    assert answer.json()["sent_on"] == "2025-06-20"
