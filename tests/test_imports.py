"""Imports: the batches an employer's own systems push across."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_imports,
)
from tare.common.types import ImportBatch
from tare.modules.imports.rules import (
    LEAST_READABLE, between, is_fit, is_open, readable_share, rows_missed,
    share_of, sort_by_received,
)
from tare.modules.imports.schemas import DecideBatch, ListBatches, ReceiveBatch
from tare.modules.imports.service import ImportsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_imports):
        seed(store)
    return store


def service():
    return ImportsService(a_store())


def a_batch(**kw) -> ImportBatch:
    base = dict(id="im-9", employer_id="em-1", kind="timesheets",
                reference="TS/2025/09", received_on="2025-06-30",
                rows_offered=240, rows_read=240, status="received")
    return ImportBatch(**{**base, **kw})


def test_batches_read_earliest_received_first():
    rows = sort_by_received([a_batch(received_on="2025-07-31"),
                             a_batch(received_on="2025-06-30")])
    assert [row.received_on for row in rows] == ["2025-06-30", "2025-07-31"]


def test_a_batch_nobody_decided_is_open():
    assert is_open(a_batch(status="received")) is True


def test_an_accepted_batch_is_no_longer_open():
    assert is_open(a_batch(status="accepted")) is False


def test_a_batch_read_in_full_reads_as_the_whole():
    assert readable_share(a_batch(rows_offered=240, rows_read=240)) == 10000


def test_a_batch_missing_a_row_reads_as_nearly_the_whole():
    assert readable_share(a_batch(rows_offered=250, rows_read=249)) == 9960


def test_a_batch_holding_nothing_reads_as_nothing_rather_than_dividing_by_nothing():
    assert readable_share(a_batch(rows_offered=0, rows_read=0)) == 0


def test_the_rows_that_did_not_come_through_are_counted():
    assert rows_missed(a_batch(rows_offered=40, rows_read=30)) == 10


def test_a_batch_read_in_full_missed_nothing():
    assert rows_missed(a_batch(rows_offered=240, rows_read=240)) == 0


def test_a_batch_read_in_full_is_fit_to_apply():
    assert is_fit(a_batch(rows_offered=240, rows_read=240)) is True


def test_a_batch_read_all_but_a_row_is_still_fit():
    assert is_fit(a_batch(rows_offered=250, rows_read=249)) is True


def test_a_batch_the_bureau_could_barely_read_is_not_fit():
    assert is_fit(a_batch(rows_offered=40, rows_read=30)) is False


def test_a_batch_exactly_on_the_bar_is_fit():
    assert readable_share(a_batch(rows_offered=10000, rows_read=9500)) == LEAST_READABLE
    assert is_fit(a_batch(rows_offered=10000, rows_read=9500)) is True


def test_batches_can_be_narrowed_to_a_window():
    assert len(between(a_store().imports.all(), "2025-07-01", "2025-07-31")) == 2


def test_a_share_of_a_row_count_is_worked_out():
    assert share_of(240, 1000) == 24


def test_the_bureau_lists_every_batch():
    assert service().list(BUREAU, ListBatches())["total"] == 4


def test_a_manager_lists_only_their_own_employers_batches():
    assert service().list(MANAGER, ListBatches())["total"] == 3


def test_a_listing_can_be_narrowed_to_what_is_still_waiting():
    assert service().list(MANAGER, ListBatches(open_only=True))["total"] == 2


def test_a_listing_can_be_narrowed_to_a_kind():
    assert service().list(MANAGER, ListBatches(kind="starters"))["total"] == 1


def test_a_batch_can_be_read():
    assert service().get(MANAGER, "im-1").rows_read == 240


def test_a_batch_nobody_sent_is_missing():
    with pytest.raises(NotFound, match="batch im-9 was not found"):
        service().get(BUREAU, "im-9")


def test_a_manager_cannot_read_another_employers_batch():
    with pytest.raises(Refused):
        service().get(MANAGER, "im-4")


def test_a_batch_is_received_and_waits():
    row = service().receive(MANAGER, ReceiveBatch(
        employer_id="em-1", kind="absences", reference="AB/2025/07",
        received_on="2025-07-31", rows_offered=20, rows_read=20))
    assert row.status == "received"


def test_something_an_employer_does_not_push_across_is_refused():
    with pytest.raises(Refused, match="is not something an employer pushes across"):
        service().receive(MANAGER, ReceiveBatch(
            employer_id="em-1", kind="poetry", reference="PO/2025/07",
            received_on="2025-07-31", rows_offered=1, rows_read=1))


def test_a_batch_cannot_read_more_rows_than_it_holds():
    with pytest.raises(Refused, match="more rows than it holds"):
        service().receive(MANAGER, ReceiveBatch(
            employer_id="em-1", kind="absences", reference="AB/2025/07",
            received_on="2025-07-31", rows_offered=10, rows_read=20))


def test_a_reference_already_received_is_refused():
    with pytest.raises(Conflict, match="already been received"):
        service().receive(MANAGER, ReceiveBatch(
            employer_id="em-1", kind="timesheets", reference="TS/2025/06",
            received_on="2025-07-31", rows_offered=1, rows_read=1))


def test_a_batch_that_came_through_is_accepted():
    assert service().decide(MANAGER, "im-2", DecideBatch(status="accepted")).status == "accepted"


def test_a_batch_too_broken_to_apply_cannot_be_accepted():
    with pytest.raises(Refused, match="too little of that batch came through"):
        service().decide(MANAGER, "im-3", DecideBatch(status="accepted"))


def test_a_batch_too_broken_to_apply_can_still_be_rejected():
    assert service().decide(MANAGER, "im-3", DecideBatch(status="rejected")).status == "rejected"


def test_a_batch_already_decided_cannot_be_decided_again():
    with pytest.raises(Conflict, match="was already accepted"):
        service().decide(MANAGER, "im-1", DecideBatch(status="rejected"))


def test_a_batch_cannot_be_put_back_to_waiting():
    with pytest.raises(Refused, match="put back to waiting"):
        service().decide(MANAGER, "im-2", DecideBatch(status="received"))


def test_the_state_of_a_batch_is_reported():
    answer = service().state(MANAGER, "im-3")
    assert answer["rows_missed"] == 10 and answer["fit"] is False


def client():
    return build_client(a_store())


def test_the_route_lists_batches():
    assert client().get("/imports", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reports_the_state_of_a_batch():
    answer = client().get("/imports/im-3/state", headers=headers(MANAGER))
    assert answer.json()["readable_share"] == 7500


def test_the_route_receives_a_batch_and_answers_201():
    answer = client().post("/imports", headers=headers(MANAGER), json={
        "employer_id": "em-1", "kind": "absences", "reference": "AB/2025/07",
        "received_on": "2025-07-31", "rows_offered": 20, "rows_read": 20})
    assert answer.status_code == 201


def test_the_route_answers_400_for_a_batch_too_broken_to_apply():
    answer = client().post("/imports/im-3/decide", headers=headers(MANAGER),
                           json={"status": "accepted"})
    assert answer.status_code == 400
