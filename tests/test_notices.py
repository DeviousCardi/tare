"""Notices: the letters the bureau sends people."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_notices,
)
from tare.common.types import Notice
from tare.modules.notices.rules import (
    days_waiting, is_late, is_waiting, sort_by_raised, waiting,
)
from tare.modules.notices.schemas import ListNotices, RaiseNotice, SendNotice
from tare.modules.notices.service import NoticesService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_notices):
        seed(store)
    return store


def service():
    return NoticesService(a_store())


def a_notice(**kw) -> Notice:
    base = dict(id="nt-9", employee_id="ee-1", employer_id="em-1", kind="payslip",
                subject="A payslip", raised_on="2025-06-28", sent_on=None)
    return Notice(**{**base, **kw})


def test_notices_read_earliest_raised_first():
    rows = sort_by_raised([a_notice(raised_on="2025-06-28"), a_notice(raised_on="2025-03-01")])
    assert [row.raised_on for row in rows] == ["2025-03-01", "2025-06-28"]


def test_a_notice_nobody_has_sent_is_waiting():
    assert is_waiting(a_notice(sent_on=None)) is True


def test_a_notice_that_has_gone_out_is_not_waiting():
    assert is_waiting(a_notice(sent_on="2025-06-29")) is False


def test_only_the_waiting_notices_survive_the_narrowing():
    rows = waiting([a_notice(id="a"), a_notice(id="b", sent_on="2025-06-29")])
    assert [row.id for row in rows] == ["a"]


def test_how_long_a_notice_has_waited_counts_both_ends():
    assert days_waiting(a_notice(raised_on="2025-06-28"), "2025-06-30") == 3


def test_a_notice_that_has_gone_out_has_waited_no_longer():
    assert days_waiting(a_notice(sent_on="2025-06-29"), "2025-07-30") == 0


def test_a_notice_raised_after_the_day_asked_about_has_waited_nothing():
    assert days_waiting(a_notice(raised_on="2025-06-28"), "2025-06-01") == 0


def test_a_notice_out_of_the_door_promptly_is_not_late():
    assert is_late(a_notice(raised_on="2025-06-28"), "2025-06-30") is False


def test_a_notice_sitting_for_weeks_is_late():
    assert is_late(a_notice(raised_on="2025-06-28"), "2025-07-30") is True


def test_the_bureau_lists_every_notice():
    assert service().list(BUREAU, ListNotices())["total"] == 4


def test_a_manager_lists_only_their_own_employers_notices():
    assert service().list(MANAGER, ListNotices())["total"] == 3


def test_a_listing_can_be_narrowed_to_what_is_still_waiting():
    assert service().list(MANAGER, ListNotices(waiting_only=True))["total"] == 2


def test_a_listing_can_be_narrowed_to_a_kind():
    assert service().list(MANAGER, ListNotices(kind="order served"))["total"] == 1


def test_a_notice_can_be_read():
    assert service().get(MANAGER, "nt-1").subject == "May payslip"


def test_a_notice_nobody_raised_is_missing():
    with pytest.raises(NotFound, match="notice nt-9 was not found"):
        service().get(BUREAU, "nt-9")


def test_a_manager_cannot_read_another_employers_notice():
    with pytest.raises(Refused):
        service().get(MANAGER, "nt-4")


def test_a_notice_is_raised_and_waits():
    row = service().raise_it(MANAGER, RaiseNotice(
        employee_id="ee-1", kind="year end", subject="Statement",
        raised_on="2025-07-01"))
    assert row.sent_on is None


def test_something_the_bureau_does_not_write_about_is_refused():
    with pytest.raises(Refused, match="is not something the bureau writes about"):
        service().raise_it(MANAGER, RaiseNotice(
            employee_id="ee-1", kind="birthday card", subject="Many happy",
            raised_on="2025-07-01"))


def test_a_notice_goes_out():
    assert service().send(MANAGER, "nt-2", SendNotice(sent_on="2025-06-30")).sent_on == "2025-06-30"


def test_a_notice_cannot_go_out_twice():
    with pytest.raises(Conflict, match="already gone out"):
        service().send(MANAGER, "nt-1", SendNotice(sent_on="2025-06-30"))


def test_a_notice_cannot_go_out_before_it_was_raised():
    with pytest.raises(Refused, match="before it was raised"):
        service().send(MANAGER, "nt-2", SendNotice(sent_on="2025-01-01"))


def test_the_notices_that_have_sat_too_long_are_reported():
    assert [row.id for row in service().late(MANAGER, "2025-07-30")] == ["nt-3", "nt-2"]


def test_nothing_is_late_on_the_day_everything_was_raised():
    assert service().late(MANAGER, "2025-03-01") == []


def client():
    return build_client(a_store())


def test_the_route_lists_notices():
    assert client().get("/notices", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reports_what_is_late():
    answer = client().get("/notices/late?on=2025-07-30", headers=headers(MANAGER))
    assert answer.json()["total"] == 2


def test_the_route_raises_a_notice_and_answers_201():
    answer = client().post("/notices", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "kind": "year end", "subject": "Statement",
        "raised_on": "2025-07-01"})
    assert answer.status_code == 201


def test_the_route_sends_a_notice():
    answer = client().post("/notices/nt-2/send", headers=headers(MANAGER),
                           json={"sent_on": "2025-06-30"})
    assert answer.json()["sent_on"] == "2025-06-30"
