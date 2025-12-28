"""Leave: the days people ask to take off, and what becomes of the asking."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_holidays, seed_leave,
)
from tare.common.types import LeaveRequest
from tare.modules.leave.rules import (
    clashes_with, counts_against_entitlement, covers, days_of, is_open, sort_by_start,
    taken_between,
)
from tare.modules.leave.schemas import AskForLeave, DecideLeave, ListLeave
from tare.modules.leave.service import LeaveService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_holidays(store)
    seed_leave(store)
    return store


def service():
    return LeaveService(a_store())


def a_request(**kw) -> LeaveRequest:
    base = dict(id="lv-9", employee_id="ee-1", employer_id="em-1",
                starts_on="2025-06-02", ends_on="2025-06-06", asked_on="2025-05-01",
                status="granted")
    return LeaveRequest(**{**base, **kw})


def test_requests_read_earliest_first():
    rows = sort_by_start([a_request(starts_on="2025-07-07"), a_request(starts_on="2025-06-02")])
    assert [row.starts_on for row in rows] == ["2025-06-02", "2025-07-07"]


def test_a_request_still_waiting_is_open():
    assert is_open(a_request(status="asked")) is True


def test_a_granted_request_is_no_longer_open():
    assert is_open(a_request(status="granted")) is False


def test_only_granted_leave_comes_off_an_entitlement():
    assert counts_against_entitlement(a_request(status="granted")) is True


def test_leave_still_being_asked_for_comes_off_nothing_yet():
    assert counts_against_entitlement(a_request(status="asked")) is False


def test_refused_leave_comes_off_nothing():
    assert counts_against_entitlement(a_request(status="refused")) is False


def test_a_request_covers_the_day_it_starts():
    assert covers(a_request(), "2025-06-02") is True


def test_a_request_covers_the_day_it_ends():
    assert covers(a_request(), "2025-06-06") is True


def test_a_request_does_not_cover_the_day_after_it_ends():
    assert covers(a_request(), "2025-06-07") is False


def test_two_live_requests_sharing_a_day_clash():
    a = a_request(starts_on="2025-06-02", ends_on="2025-06-06")
    b = a_request(starts_on="2025-06-06", ends_on="2025-06-06")
    assert clashes_with(a, b) is True


def test_a_withdrawn_request_clashes_with_nothing():
    a = a_request(starts_on="2025-06-02", ends_on="2025-06-06", status="withdrawn")
    b = a_request(starts_on="2025-06-06", ends_on="2025-06-06")
    assert clashes_with(a, b) is False


def test_a_refused_request_clashes_with_nothing():
    a = a_request(starts_on="2025-06-02", ends_on="2025-06-06", status="refused")
    b = a_request(starts_on="2025-06-04", ends_on="2025-06-06")
    assert clashes_with(a, b) is False


# Every run of leave below sits inside one working week, Monday to Friday, so
# the days it uses up do not depend on how a weekend inside a run is treated.
def test_a_working_week_of_leave_uses_five_days():
    assert days_of(a_request(starts_on="2025-06-02", ends_on="2025-06-06"), []) == 5


def test_a_single_day_of_leave_uses_one_day():
    assert days_of(a_request(starts_on="2025-06-02", ends_on="2025-06-02"), []) == 1


def test_three_days_of_leave_use_three_days():
    assert days_of(a_request(starts_on="2025-06-02", ends_on="2025-06-04"), []) == 3


def test_granted_leave_in_a_window_is_counted():
    mine = [row for row in a_store().leave.all() if row.employee_id == "ee-1"]
    assert taken_between(mine, "2025-06-01", "2025-06-30", []) == 5


def test_leave_still_being_asked_for_is_not_counted():
    mine = [row for row in a_store().leave.all() if row.employee_id == "ee-1"]
    assert taken_between(mine, "2025-10-01", "2025-10-31", []) == 0


def test_leave_across_a_whole_year_adds_its_granted_runs_up():
    mine = [row for row in a_store().leave.all() if row.employee_id == "ee-1"]
    assert taken_between(mine, "2025-01-01", "2025-12-31", []) == 10


def test_the_bureau_lists_every_request():
    assert service().list(BUREAU, ListLeave())["total"] == 4


def test_a_manager_lists_only_their_own_employers_requests():
    assert service().list(MANAGER, ListLeave())["total"] == 3


def test_a_listing_can_be_narrowed_to_what_is_still_waiting():
    assert service().list(MANAGER, ListLeave(status="asked"))["total"] == 1


def test_a_listing_can_be_narrowed_to_a_day():
    assert service().list(MANAGER, ListLeave(covering="2025-06-03"))["total"] == 1


def test_a_request_can_be_read():
    assert service().get(MANAGER, "lv-1").status == "granted"


def test_a_request_nobody_made_is_missing():
    with pytest.raises(NotFound, match="leave request lv-9 was not found"):
        service().get(BUREAU, "lv-9")


def test_a_manager_cannot_read_another_employers_request():
    with pytest.raises(Refused):
        service().get(MANAGER, "lv-4")


def test_leave_is_asked_for_and_starts_out_waiting():
    row = service().ask(MANAGER, AskForLeave(
        employee_id="ee-1", starts_on="2025-11-03", ends_on="2025-11-07",
        asked_on="2025-10-01"))
    assert row.status == "asked"


def test_leave_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().ask(MANAGER, AskForLeave(
            employee_id="ee-1", starts_on="2025-11-07", ends_on="2025-11-03",
            asked_on="2025-10-01"))


def test_leave_cannot_be_asked_for_after_it_has_started():
    with pytest.raises(Refused, match="after it has started"):
        service().ask(MANAGER, AskForLeave(
            employee_id="ee-1", starts_on="2025-11-03", ends_on="2025-11-07",
            asked_on="2025-11-05"))


def test_leave_running_into_leave_already_granted_is_refused():
    with pytest.raises(Conflict, match="already has leave across"):
        service().ask(MANAGER, AskForLeave(
            employee_id="ee-1", starts_on="2025-06-04", ends_on="2025-06-10",
            asked_on="2025-05-01"))


def test_a_request_is_granted():
    assert service().decide(MANAGER, "lv-3", DecideLeave(status="granted")).status == "granted"


def test_a_request_is_refused():
    assert service().decide(MANAGER, "lv-3", DecideLeave(status="refused")).status == "refused"


def test_a_request_already_decided_cannot_be_decided_again():
    with pytest.raises(Conflict, match="was already granted"):
        service().decide(MANAGER, "lv-1", DecideLeave(status="refused"))


def test_a_request_cannot_be_put_back_to_waiting():
    with pytest.raises(Refused, match="cannot be put back to waiting"):
        service().decide(MANAGER, "lv-3", DecideLeave(status="asked"))


def test_something_a_request_cannot_become_is_refused():
    with pytest.raises(Refused, match="is not something a request can become"):
        service().decide(MANAGER, "lv-3", DecideLeave(status="forgotten"))


def test_granting_a_request_brings_its_days_into_the_total():
    svc = service()
    svc.decide(MANAGER, "lv-3", DecideLeave(status="granted"))
    assert svc.taken(MANAGER, "ee-1", "2025-10-01", "2025-10-31")["days"] == 5


def test_the_days_a_request_uses_are_reported():
    assert service().days(MANAGER, "lv-1") == 5


def client():
    return build_client(a_store())


def test_the_route_lists_requests():
    assert client().get("/leave", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reports_leave_taken_in_a_window():
    answer = client().get("/leave/taken/ee-1?start=2025-01-01&end=2025-12-31",
                          headers=headers(MANAGER))
    assert answer.json()["days"] == 10


def test_the_route_asks_for_leave_and_answers_201():
    answer = client().post("/leave", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "starts_on": "2025-11-03", "ends_on": "2025-11-07",
        "asked_on": "2025-10-01"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_leave_over_leave_already_granted():
    answer = client().post("/leave", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "starts_on": "2025-06-04", "ends_on": "2025-06-10",
        "asked_on": "2025-05-01"})
    assert answer.status_code == 409


def test_the_route_decides_a_request():
    answer = client().post("/leave/lv-3/decide", headers=headers(MANAGER),
                           json={"status": "granted"})
    assert answer.json()["status"] == "granted"
