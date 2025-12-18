"""Timesheets: the hours people put in, and what a window of them comes to."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_elements, seed_employees,
    seed_employers, seed_timesheets,
)
from tare.common.types import TimesheetLine
from tare.modules.timesheets.rules import (
    approved_only, between, days_worked, hours_between, hours_by_element, sort_by_day,
)
from tare.modules.timesheets.schemas import ApproveLine, ListTimesheets, RecordHours
from tare.modules.timesheets.service import TimesheetsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_elements(store)
    seed_timesheets(store)
    return store


def service():
    return TimesheetsService(a_store())


def mine():
    return [row for row in a_store().timesheets.all() if row.employee_id == "ee-1"]


def a_line(**kw) -> TimesheetLine:
    base = dict(id="ts-9", employee_id="ee-1", employer_id="em-1",
                worked_on="2025-06-02", hours=8, element_id="el-1", approved=True)
    return TimesheetLine(**{**base, **kw})


def test_lines_read_earliest_first():
    rows = sort_by_day([a_line(worked_on="2025-06-03"), a_line(worked_on="2025-06-02")])
    assert [row.worked_on for row in rows] == ["2025-06-02", "2025-06-03"]


def test_only_approved_lines_survive_the_narrowing():
    rows = approved_only([a_line(id="a"), a_line(id="b", approved=False)])
    assert [row.id for row in rows] == ["a"]


def test_a_window_takes_a_line_on_its_first_day():
    assert len(between(mine(), "2025-06-02", "2025-06-02")) == 1


def test_a_window_takes_a_line_on_its_last_day():
    assert len(between(mine(), "2025-06-06", "2025-06-06")) == 1


def test_a_window_leaves_out_a_line_outside_it():
    assert between(mine(), "2025-07-01", "2025-07-31") == []


def test_approved_hours_across_a_window_are_added_up():
    assert hours_between(mine(), "2025-06-02", "2025-06-08") == 27


def test_a_line_still_waiting_on_approval_is_not_counted():
    # The Friday's five hours are unapproved, so they stay out of the 27.
    assert hours_between(mine(), "2025-06-06", "2025-06-06") == 0


def test_a_window_with_nothing_in_it_comes_to_nothing():
    assert hours_between(mine(), "2025-07-01", "2025-07-31") == 0


def test_hours_are_split_by_what_they_are_paid_as():
    assert hours_by_element(mine(), "2025-06-02", "2025-06-08") == {"el-1": 24, "el-2": 3}


def test_the_split_leaves_out_unapproved_hours():
    assert "el-1" in hours_by_element(mine(), "2025-06-02", "2025-06-04")


def test_the_days_somebody_worked_are_counted():
    assert days_worked(mine(), "2025-06-02", "2025-06-08") == 4


def test_a_day_carrying_no_hours_is_not_a_day_worked():
    assert days_worked([a_line(hours=0)], "2025-06-02", "2025-06-02") == 0


def test_the_bureau_lists_every_line():
    assert service().list(BUREAU, ListTimesheets())["total"] == 6


def test_a_manager_lists_only_their_own_employers_lines():
    assert service().list(MANAGER, ListTimesheets())["total"] == 5


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListTimesheets(employee_id="ee-1"))["total"] == 5


def test_a_listing_can_be_narrowed_to_what_is_approved():
    assert service().list(MANAGER, ListTimesheets(approved_only=True))["total"] == 4


def test_a_listing_can_be_narrowed_to_a_window():
    answer = service().list(MANAGER, ListTimesheets(start="2025-06-02", end="2025-06-03"))
    assert answer["total"] == 2


def test_a_line_can_be_read():
    assert service().get(MANAGER, "ts-1").hours == 8


def test_a_line_nobody_recorded_is_missing():
    with pytest.raises(NotFound, match="timesheet line ts-9 was not found"):
        service().get(BUREAU, "ts-9")


def test_a_manager_cannot_read_another_employers_line():
    with pytest.raises(Refused):
        service().get(MANAGER, "ts-6")


def test_hours_are_recorded_and_wait_on_approval():
    row = service().record(MANAGER, RecordHours(
        employee_id="ee-1", worked_on="2025-06-09", hours=8, element_id="el-1"))
    assert row.approved is False


def test_the_same_element_twice_on_one_day_is_refused():
    with pytest.raises(Conflict, match="already has BASIC hours"):
        service().record(MANAGER, RecordHours(
            employee_id="ee-1", worked_on="2025-06-02", hours=2, element_id="el-1"))


def test_a_second_element_on_one_day_is_allowed():
    assert service().record(MANAGER, RecordHours(
        employee_id="ee-1", worked_on="2025-06-02", hours=2, element_id="el-2")).hours == 2


def test_hours_cannot_be_recorded_against_a_deduction():
    with pytest.raises(Refused, match="cannot be recorded against a deduction"):
        service().record(MANAGER, RecordHours(
            employee_id="ee-1", worked_on="2025-06-09", hours=8, element_id="el-4"))


def test_hours_cannot_be_paid_as_another_employers_element():
    with pytest.raises(Refused, match="person's own employer"):
        service().record(MANAGER, RecordHours(
            employee_id="ee-1", worked_on="2025-06-09", hours=8, element_id="el-5"))


def test_hours_cannot_be_recorded_for_a_day_somebody_was_not_in_post():
    with pytest.raises(Refused, match="was not in post on"):
        service().record(MANAGER, RecordHours(
            employee_id="ee-3", worked_on="2025-08-01", hours=8, element_id="el-1"))


def test_a_line_is_approved():
    assert service().approve(MANAGER, "ts-5", ApproveLine()).approved is True


def test_a_line_already_approved_cannot_be_approved_again():
    with pytest.raises(Conflict, match="already in the state"):
        service().approve(MANAGER, "ts-1", ApproveLine())


def test_an_approval_can_be_taken_back():
    assert service().approve(MANAGER, "ts-1", ApproveLine(approved=False)).approved is False


def test_approving_a_line_brings_its_hours_into_the_total():
    svc = service()
    svc.approve(MANAGER, "ts-5", ApproveLine())
    assert svc.hours(MANAGER, "ee-1", "2025-06-02", "2025-06-08")["hours"] == 32


def test_an_unapproved_line_can_be_withdrawn():
    svc = service()
    svc.withdraw(MANAGER, "ts-5")
    with pytest.raises(NotFound):
        svc.get(MANAGER, "ts-5")


def test_an_approved_line_cannot_be_withdrawn():
    with pytest.raises(Refused, match="approved line cannot be withdrawn"):
        service().withdraw(MANAGER, "ts-1")


def test_what_a_window_of_hours_comes_to_is_reported():
    answer = service().hours(MANAGER, "ee-1", "2025-06-02", "2025-06-08")
    assert answer["hours"] == 27 and answer["days_worked"] == 4


def client():
    return build_client(a_store())


def test_the_route_lists_lines():
    assert client().get("/timesheets", headers=headers(BUREAU)).json()["total"] == 6


def test_the_route_reports_what_a_window_comes_to():
    answer = client().get("/timesheets/hours/ee-1?start=2025-06-02&end=2025-06-08",
                          headers=headers(MANAGER))
    assert answer.json()["hours"] == 27


def test_the_route_records_hours_and_answers_201():
    answer = client().post("/timesheets", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "worked_on": "2025-06-09", "hours": 8,
        "element_id": "el-1"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_the_same_element_twice_on_a_day():
    answer = client().post("/timesheets", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "worked_on": "2025-06-02", "hours": 2,
        "element_id": "el-1"})
    assert answer.status_code == 409


def test_the_route_approves_a_line():
    answer = client().post("/timesheets/ts-5/approve", headers=headers(MANAGER),
                           json={"approved": True})
    assert answer.json()["approved"] is True


def test_the_route_withdraws_an_unapproved_line_and_answers_204():
    assert client().delete("/timesheets/ts-5", headers=headers(MANAGER)).status_code == 204


def test_the_route_refuses_more_hours_than_a_day_holds():
    answer = client().post("/timesheets", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "worked_on": "2025-06-09", "hours": 30,
        "element_id": "el-1"})
    assert answer.status_code == 422
