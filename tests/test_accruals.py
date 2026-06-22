"""Accruals: leave earned as it is worked, rather than granted up front."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_accruals, seed_employees,
    seed_employers,
)
from tare.common.types import LeaveAccrual
from tare.modules.accruals.rules import (
    HOURS_IN_A_DAY, as_days, earned_by, earned_in_year, sort_by_period,
    worked_in_year,
)
from tare.modules.accruals.schemas import ListAccruals, RecordAccrual
from tare.modules.accruals.service import AccrualsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_accruals):
        seed(store)
    return store


def service():
    return AccrualsService(a_store())


def an_accrual(**kw) -> LeaveAccrual:
    base = dict(id="ac-9", employee_id="ee-2", employer_id="em-1",
                year_starts_on="2025-04-06", period=4, hours_worked=160,
                hours_earned=19)
    return LeaveAccrual(**{**base, **kw})


def test_accruals_read_by_period():
    rows = sort_by_period([an_accrual(period=6), an_accrual(period=4)])
    assert [row.period for row in rows] == [4, 6]


def test_a_month_of_hours_earns_its_share_of_leave():
    assert earned_by(160) == 19


def test_a_shorter_month_earns_less():
    assert earned_by(152) == 18


def test_a_longer_month_earns_more():
    assert earned_by(168) == 20


def test_no_hours_earn_nothing():
    assert earned_by(0) == 0


def test_negative_hours_earn_nothing():
    assert earned_by(-40) == 0


def test_what_is_earned_rounds_half_up_rather_than_truncating():
    # 100 hours at 12.07% is 12.07, which rounds to 12; 104 is 12.55 and
    # rounds to 13.
    assert earned_by(100) == 12 and earned_by(104) == 13


def test_the_year_adds_the_periods_behind_it_up():
    assert earned_in_year(a_store().accruals.all(), "ee-2", "2025-04-06") == 57


def test_the_hours_worked_across_the_year_are_added_up_too():
    assert worked_in_year(a_store().accruals.all(), "ee-2", "2025-04-06") == 480


def test_a_year_nobody_worked_earns_nothing():
    assert earned_in_year(a_store().accruals.all(), "ee-2", "2024-04-06") == 0


def test_somebody_who_accrues_nothing_has_earned_nothing():
    assert earned_in_year(a_store().accruals.all(), "ee-1", "2025-04-06") == 0


def test_earned_hours_read_back_as_whole_days():
    assert as_days(HOURS_IN_A_DAY * 3) == 3


def test_half_a_day_of_leave_is_not_a_day():
    assert as_days(HOURS_IN_A_DAY * 2 + 4) == 2


def test_less_than_a_day_is_no_days():
    assert as_days(4) == 0


def test_the_bureau_lists_every_accrual():
    assert service().list(BUREAU, ListAccruals())["total"] == 3


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListAccruals(employee_id="ee-2"))["total"] == 3


def test_a_listing_can_be_narrowed_to_a_leave_year():
    assert service().list(MANAGER, ListAccruals(year_starts_on="2024-04-06"))["total"] == 0


def test_an_accrual_can_be_read():
    assert service().get(MANAGER, "ac-1").hours_earned == 19


def test_an_accrual_nobody_recorded_is_missing():
    with pytest.raises(NotFound, match="accrual ac-9 was not found"):
        service().get(BUREAU, "ac-9")


def test_an_accrual_is_recorded_and_works_out_what_was_earned():
    row = service().record(MANAGER, RecordAccrual(
        employee_id="ee-2", year_starts_on="2025-04-06", period=7,
        hours_worked=160))
    assert row.hours_earned == 19


def test_a_second_accrual_for_one_period_is_refused():
    with pytest.raises(Conflict, match="already has an accrual for period"):
        service().record(MANAGER, RecordAccrual(
            employee_id="ee-2", year_starts_on="2025-04-06", period=4,
            hours_worked=160))


def test_a_manager_cannot_record_against_another_employers_person():
    with pytest.raises(Refused):
        service().record(MANAGER, RecordAccrual(
            employee_id="ee-4", year_starts_on="2025-04-06", period=7,
            hours_worked=160))


def test_what_somebody_has_earned_so_far_is_reported():
    answer = service().earned(MANAGER, "ee-2", "2025-04-06")
    assert answer["hours_earned"] == 57 and answer["days_earned"] == 7


def test_recording_an_accrual_adds_to_what_has_been_earned():
    svc = service()
    svc.record(MANAGER, RecordAccrual(
        employee_id="ee-2", year_starts_on="2025-04-06", period=7, hours_worked=160))
    assert svc.earned(MANAGER, "ee-2", "2025-04-06")["hours_earned"] == 76


def client():
    return build_client(a_store())


def test_the_route_lists_accruals():
    assert client().get("/accruals", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_what_has_been_earned():
    answer = client().get("/accruals/earned/ee-2?year_starts_on=2025-04-06",
                          headers=headers(MANAGER))
    assert answer.json()["days_earned"] == 7


def test_the_route_records_an_accrual_and_answers_201():
    answer = client().post("/accruals", headers=headers(MANAGER), json={
        "employee_id": "ee-2", "year_starts_on": "2025-04-06", "period": 7,
        "hours_worked": 160})
    assert answer.status_code == 201


def test_the_route_refuses_more_hours_than_a_period_could_hold():
    answer = client().post("/accruals", headers=headers(MANAGER), json={
        "employee_id": "ee-2", "year_starts_on": "2025-04-06", "period": 7,
        "hours_worked": 5000})
    assert answer.status_code == 422
