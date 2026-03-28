"""Continuity: how long somebody has really been with an employer."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_service,
)
from tare.common.types import ServiceRecord
from tare.modules.continuity.rules import (
    continuous_from, gap_between, joins_up, service_days, service_years, sort_by_start,
)
from tare.modules.continuity.schemas import EndService, ListService, RecordService
from tare.modules.continuity.service import ContinuityService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_service):
        seed(store)
    return store


def service():
    return ContinuityService(a_store())


def a_record(**kw) -> ServiceRecord:
    base = dict(id="sr-9", employee_id="ee-1", employer_id="em-1",
                started_on="2020-04-06", ended_on=None, reason="Joined")
    return ServiceRecord(**{**base, **kw})


def test_records_read_earliest_first():
    rows = sort_by_start([a_record(started_on="2021-01-11"), a_record(started_on="2019-01-07")])
    assert [row.started_on for row in rows] == ["2019-01-07", "2021-01-11"]


def test_runs_that_touch_have_no_gap_between_them():
    a = a_record(started_on="2020-01-01", ended_on="2020-06-30")
    assert gap_between(a, a_record(started_on="2020-07-01")) == 0


def test_the_gap_counts_the_days_actually_between_two_runs():
    a = a_record(started_on="2020-01-01", ended_on="2020-06-30")
    assert gap_between(a, a_record(started_on="2020-07-06")) == 5


def test_a_run_that_never_ended_has_no_gap_after_it():
    a = a_record(started_on="2020-01-01", ended_on=None)
    assert gap_between(a, a_record(started_on="2021-01-01")) == 0


# The seeded runs either touch or are broken by the better part of a year, so
# whether they join up does not depend on how a break landing exactly on the
# limit is read.
def test_runs_that_touch_join_up():
    a = a_record(started_on="2020-01-01", ended_on="2020-06-30")
    assert joins_up(a, a_record(started_on="2020-07-01")) is True


def test_a_break_of_a_few_days_still_joins_up():
    a = a_record(started_on="2020-01-01", ended_on="2020-06-30")
    assert joins_up(a, a_record(started_on="2020-07-06")) is True


def test_a_break_of_months_does_not_join_up():
    a = a_record(started_on="2020-01-01", ended_on="2020-06-30")
    assert joins_up(a, a_record(started_on="2021-01-11")) is False


def test_continuous_service_runs_from_the_day_somebody_joined():
    assert continuous_from(a_store().service.all(), "ee-1") == "2020-04-06"


def test_continuous_service_starts_again_after_a_long_break():
    assert continuous_from(a_store().service.all(), "ee-3") == "2021-01-11"


def test_somebody_with_no_record_has_no_continuous_service():
    assert continuous_from(a_store().service.all(), "ee-9") is None


def test_service_days_count_both_ends():
    assert service_days(a_store().service.all(), "ee-1", "2020-04-06") == 1


def test_service_days_before_somebody_joined_are_nothing():
    assert service_days(a_store().service.all(), "ee-1", "2019-01-01") == 0


def test_service_in_whole_years_counts_at_three_hundred_and_sixty_five_days():
    assert service_years(a_store().service.all(), "ee-1", "2021-04-05") == 1


def test_the_bureau_lists_every_record():
    assert service().list(BUREAU, ListService())["total"] == 4


def test_a_manager_lists_only_their_own_employers_records():
    assert service().list(MANAGER, ListService())["total"] == 3


def test_a_record_can_be_read():
    assert service().get(MANAGER, "sr-1").reason == "Joined"


def test_a_record_nobody_made_is_missing():
    with pytest.raises(NotFound, match="service record sr-9 was not found"):
        service().get(BUREAU, "sr-9")


def test_a_manager_cannot_read_another_employers_record():
    with pytest.raises(Refused):
        service().get(MANAGER, "sr-4")


def test_a_run_of_service_is_recorded():
    row = service().record(MANAGER, RecordService(
        employee_id="ee-2", started_on="2025-07-01", reason="Joined"))
    assert row.ended_on is None


def test_a_second_open_run_is_refused():
    with pytest.raises(Conflict, match="already has a run of service open"):
        service().record(MANAGER, RecordService(
            employee_id="ee-1", started_on="2025-07-01", reason="Again"))


def test_a_run_of_service_is_ended():
    assert service().end(MANAGER, "sr-1", EndService(ended_on="2025-09-30")).ended_on == "2025-09-30"


def test_a_run_of_service_cannot_end_twice():
    with pytest.raises(Conflict, match="already ended"):
        service().end(MANAGER, "sr-2", EndService(ended_on="2025-09-30"))


def test_a_run_of_service_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().end(MANAGER, "sr-1", EndService(ended_on="2019-01-01"))


def test_somebodys_continuity_is_reported():
    answer = service().of(MANAGER, "ee-1", "2021-04-05")
    assert answer["continuous_from"] == "2020-04-06" and answer["years"] == 1


def client():
    return build_client(a_store())


def test_the_route_lists_records():
    assert client().get("/continuity", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reports_continuity():
    answer = client().get("/continuity/of/ee-1?upto=2021-04-05", headers=headers(MANAGER))
    assert answer.json()["years"] == 1


def test_the_route_records_a_run_and_answers_201():
    answer = client().post("/continuity", headers=headers(MANAGER), json={
        "employee_id": "ee-2", "started_on": "2025-07-01", "reason": "Joined"})
    assert answer.status_code == 201


def test_the_route_ends_a_run():
    answer = client().post("/continuity/sr-1/end", headers=headers(MANAGER),
                           json={"ended_on": "2025-09-30"})
    assert answer.json()["ended_on"] == "2025-09-30"
