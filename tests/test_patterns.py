"""Working patterns: the hours somebody is expected to work."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_patterns,
)
from tare.common.types import WorkingPattern
from tare.modules.patterns.rules import (
    expected_between, hours_on, overtime_above, sort_by_start, standing_for, stands_on,
    weekly_hours,
)
from tare.modules.patterns.schemas import EndPattern, ListPatterns, SetPattern
from tare.modules.patterns.service import PatternsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_patterns(store)
    return store


def service():
    return PatternsService(a_store())


def a_pattern(**kw) -> WorkingPattern:
    base = dict(id="wp-9", employee_id="ee-1", employer_id="em-1",
                starts_on="2025-01-01", ends_on=None, hours=[8, 8, 8, 8, 5, 0, 0])
    return WorkingPattern(**{**base, **kw})


def test_patterns_read_earliest_first():
    rows = sort_by_start([a_pattern(starts_on="2025-06-01"), a_pattern(starts_on="2025-01-01")])
    assert [row.starts_on for row in rows] == ["2025-01-01", "2025-06-01"]


def test_a_pattern_stands_on_the_day_it_starts():
    assert stands_on(a_pattern(starts_on="2025-01-01"), "2025-01-01") is True


def test_a_pattern_does_not_stand_the_day_before_it_starts():
    assert stands_on(a_pattern(starts_on="2025-01-01"), "2024-12-31") is False


def test_a_pattern_still_stands_on_the_day_it_ends():
    assert stands_on(a_pattern(starts_on="2025-01-01", ends_on="2025-06-30"), "2025-06-30") is True


def test_a_pattern_does_not_stand_the_day_after_it_ends():
    assert stands_on(a_pattern(starts_on="2025-01-01", ends_on="2025-06-30"), "2025-07-01") is False


def test_the_pattern_somebody_is_on_is_found():
    assert standing_for(a_store().patterns.all(), "ee-1", "2025-06-01").id == "wp-1"


def test_the_latest_pattern_wins_where_two_cover_a_day():
    rows = [a_pattern(id="a", starts_on="2025-01-01"), a_pattern(id="b", starts_on="2025-06-01")]
    assert standing_for(rows, "ee-1", "2025-08-01").id == "b"


def test_nobody_is_on_a_pattern_before_it_starts():
    assert standing_for(a_store().patterns.all(), "ee-2", "2025-01-01") is None


# Every seeded pattern is worked Monday to Friday with nil at the weekend, so
# the weekly figure does not depend on how a weekend entry is treated.
def test_a_full_week_of_the_pattern_comes_to_its_contracted_hours():
    assert weekly_hours(a_pattern(hours=[8, 8, 8, 8, 5, 0, 0])) == 37


def test_a_part_week_comes_to_less():
    assert weekly_hours(a_pattern(hours=[4, 4, 4, 4, 4, 0, 0])) == 20


def test_a_pattern_of_no_hours_comes_to_nothing():
    assert weekly_hours(a_pattern(hours=[0] * 7)) == 0


def test_a_monday_reads_the_first_figure_of_the_pattern():
    # 2025-06-02 is a Monday.
    assert hours_on(a_pattern(hours=[8, 7, 6, 5, 4, 3, 2]), "2025-06-02") == 8


def test_a_friday_reads_the_fifth_figure_of_the_pattern():
    assert hours_on(a_pattern(hours=[8, 7, 6, 5, 4, 3, 2]), "2025-06-06") == 4


def test_a_sunday_reads_the_last_figure_of_the_pattern():
    assert hours_on(a_pattern(hours=[8, 7, 6, 5, 4, 3, 2]), "2025-06-08") == 2


def test_a_working_week_expects_the_pattern_across_it():
    # Monday 2025-06-02 to Sunday 2025-06-08.
    assert expected_between(a_pattern(), "2025-06-02", "2025-06-08") == 37


def test_a_single_day_expects_only_that_day():
    assert expected_between(a_pattern(), "2025-06-02", "2025-06-02") == 8


def test_a_window_before_the_pattern_started_expects_nothing():
    assert expected_between(a_pattern(starts_on="2025-07-01"), "2025-06-02", "2025-06-08") == 0


def test_hours_beyond_the_pattern_are_overtime():
    assert overtime_above(a_pattern(), 42) == 5


def test_hours_matching_the_pattern_are_no_overtime():
    assert overtime_above(a_pattern(), 37) == 0


def test_hours_short_of_the_pattern_are_no_overtime():
    assert overtime_above(a_pattern(), 30) == 0


def test_negative_hours_worked_are_refused():
    with pytest.raises(Refused, match="cannot be negative"):
        overtime_above(a_pattern(), -1)


def test_the_bureau_lists_every_pattern():
    assert service().list(BUREAU, ListPatterns())["total"] == 3


def test_a_manager_lists_only_their_own_employers_patterns():
    assert service().list(MANAGER, ListPatterns())["total"] == 2


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListPatterns(employee_id="ee-1"))["total"] == 1


def test_a_pattern_can_be_read():
    assert service().get(MANAGER, "wp-1").hours == [8, 8, 8, 8, 5, 0, 0]


def test_a_pattern_nobody_set_is_missing():
    with pytest.raises(NotFound, match="pattern wp-9 was not found"):
        service().get(BUREAU, "wp-9")


def test_a_manager_cannot_read_another_employers_pattern():
    with pytest.raises(Refused):
        service().get(MANAGER, "wp-3")


def test_a_pattern_is_set():
    row = service().set(MANAGER, SetPattern(
        employee_id="ee-3", starts_on="2025-08-01", hours=[6, 6, 6, 6, 6, 0, 0]))
    assert row.employer_id == "em-1"


def test_setting_a_pattern_ends_the_one_before_it_the_day_before():
    svc = service()
    svc.set(MANAGER, SetPattern(
        employee_id="ee-1", starts_on="2025-06-01", hours=[7, 7, 7, 7, 7, 0, 0]))
    assert svc.get(MANAGER, "wp-1").ends_on == "2025-05-31"


def test_a_second_pattern_starting_the_same_day_is_refused():
    with pytest.raises(Conflict, match="already starts on"):
        service().set(MANAGER, SetPattern(
            employee_id="ee-1", starts_on="2020-04-06", hours=[1] * 7))


def test_a_pattern_cannot_start_before_the_person_joined():
    with pytest.raises(Refused, match="before the person joined"):
        service().set(MANAGER, SetPattern(
            employee_id="ee-2", starts_on="2024-01-01", hours=[1] * 7))


def test_a_day_of_more_than_twenty_four_hours_is_refused():
    with pytest.raises(Refused, match="more than 24"):
        service().set(MANAGER, SetPattern(
            employee_id="ee-3", starts_on="2025-08-01", hours=[25, 0, 0, 0, 0, 0, 0]))


def test_a_pattern_is_ended():
    assert service().end(MANAGER, "wp-1", EndPattern(ends_on="2025-09-30")).ends_on == "2025-09-30"


def test_a_pattern_cannot_end_twice():
    svc = service()
    svc.end(MANAGER, "wp-1", EndPattern(ends_on="2025-09-30"))
    with pytest.raises(Conflict, match="already ended"):
        svc.end(MANAGER, "wp-1", EndPattern(ends_on="2025-10-31"))


def test_what_a_pattern_expects_across_a_window_is_reported():
    assert service().expected(MANAGER, "ee-1", "2025-06-02", "2025-06-08")["hours"] == 37


def test_the_overtime_a_week_carried_is_reported():
    assert service().overtime(MANAGER, "ee-1", "2025-06-02", 42) == 5


def client():
    return build_client(a_store())


def test_the_route_lists_patterns():
    assert client().get("/patterns", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_the_pattern_somebody_is_on():
    answer = client().get("/patterns/standing/ee-1?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["id"] == "wp-1"


def test_the_route_reports_what_a_window_expects():
    answer = client().get("/patterns/expected/ee-1?start=2025-06-02&end=2025-06-08",
                          headers=headers(MANAGER))
    assert answer.json()["hours"] == 37


def test_the_route_reports_overtime():
    answer = client().get("/patterns/overtime/ee-1?on=2025-06-02&worked=42",
                          headers=headers(MANAGER))
    assert answer.json()["overtime"] == 5


def test_the_route_sets_a_pattern_and_answers_201():
    answer = client().post("/patterns", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "starts_on": "2025-08-01", "hours": [6, 6, 6, 6, 6, 0, 0]})
    assert answer.status_code == 201


def test_the_route_refuses_a_pattern_that_is_not_seven_days_long():
    answer = client().post("/patterns", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "starts_on": "2025-08-01", "hours": [6, 6, 6]})
    assert answer.status_code == 422
