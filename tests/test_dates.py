"""Calendar dates, windows that include both ends, and working days."""

import pytest

from tare.common.dates import (
    add_days, add_working_days, compare_dates, days_inclusive, is_calendar_date,
    is_weekend, is_working_day, on_or_after_working_day, overlaps, within_window,
    working_days_inclusive,
)
from tare.common.errors import Refused

# 2025-04-04 is a Friday, 2025-04-05 a Saturday, 2025-04-07 a Monday.
HOLIDAYS = ["2025-04-07", "2025-12-25", "2025-12-26"]


def test_a_real_day_is_a_calendar_date():
    assert is_calendar_date("2025-04-04") is True


def test_a_day_that_never_happened_is_not_a_calendar_date():
    assert is_calendar_date("2025-02-30") is False


def test_a_month_that_does_not_exist_is_not_a_calendar_date():
    assert is_calendar_date("2025-13-01") is False


def test_something_that_is_not_a_date_at_all_is_not_a_calendar_date():
    assert is_calendar_date("not a day") is False


def test_a_date_without_its_padding_is_not_a_calendar_date():
    assert is_calendar_date("2025-4-4") is False


def test_a_leap_day_in_a_leap_year_is_a_calendar_date():
    assert is_calendar_date("2024-02-29") is True


def test_a_leap_day_in_an_ordinary_year_is_not():
    assert is_calendar_date("2025-02-29") is False


def test_an_earlier_day_compares_below_a_later_one():
    assert compare_dates("2025-04-01", "2025-04-02") == -1


def test_a_later_day_compares_above_an_earlier_one():
    assert compare_dates("2025-04-02", "2025-04-01") == 1


def test_the_same_day_compares_equal():
    assert compare_dates("2025-04-01", "2025-04-01") == 0


def test_comparing_something_that_is_not_a_date_is_refused():
    with pytest.raises(Refused, match="not a calendar date"):
        compare_dates("2025-02-30", "2025-04-01")


def test_stepping_days_on_crosses_the_month_end():
    assert add_days("2025-04-30", 1) == "2025-05-01"


def test_stepping_days_back_crosses_the_year_end():
    assert add_days("2025-01-01", -1) == "2024-12-31"


def test_stepping_no_days_stays_where_it_is():
    assert add_days("2025-04-04", 0) == "2025-04-04"


def test_a_window_counts_both_of_its_ends():
    assert days_inclusive("2025-04-01", "2025-04-30") == 30


def test_a_window_of_one_day_counts_that_day():
    assert days_inclusive("2025-04-04", "2025-04-04") == 1


def test_a_window_that_ends_before_it_starts_is_refused():
    with pytest.raises(Refused, match="ends before it starts"):
        days_inclusive("2025-04-30", "2025-04-01")


def test_the_first_day_of_a_window_is_inside_it():
    assert within_window("2025-04-01", "2025-04-01", "2025-04-30") is True


def test_the_last_day_of_a_window_is_inside_it():
    assert within_window("2025-04-30", "2025-04-01", "2025-04-30") is True


def test_the_day_before_a_window_is_outside_it():
    assert within_window("2025-03-31", "2025-04-01", "2025-04-30") is False


def test_the_day_after_a_window_is_outside_it():
    assert within_window("2025-05-01", "2025-04-01", "2025-04-30") is False


def test_two_windows_that_share_a_single_day_overlap():
    assert overlaps("2025-04-01", "2025-04-10", "2025-04-10", "2025-04-20") is True


def test_two_windows_that_touch_without_sharing_a_day_do_not_overlap():
    assert overlaps("2025-04-01", "2025-04-09", "2025-04-10", "2025-04-20") is False


def test_a_window_inside_another_overlaps_it():
    assert overlaps("2025-04-05", "2025-04-06", "2025-04-01", "2025-04-30") is True


def test_a_saturday_is_a_weekend():
    assert is_weekend("2025-04-05") is True


def test_a_sunday_is_a_weekend():
    assert is_weekend("2025-04-06") is True


def test_a_friday_is_not_a_weekend():
    assert is_weekend("2025-04-04") is False


def test_a_weekday_the_calendar_leaves_alone_is_a_working_day():
    assert is_working_day("2025-04-04", HOLIDAYS) is True


def test_a_weekday_the_calendar_holds_as_a_holiday_is_not_a_working_day():
    assert is_working_day("2025-04-07", HOLIDAYS) is False


def test_a_saturday_is_not_a_working_day_even_with_an_empty_calendar():
    assert is_working_day("2025-04-05", []) is False


def test_a_working_day_stays_where_it_is():
    assert on_or_after_working_day("2025-04-04", HOLIDAYS) == "2025-04-04"


def test_a_saturday_steps_to_the_next_working_day():
    # Monday the 7th is a holiday, so it lands on the Tuesday.
    assert on_or_after_working_day("2025-04-05", HOLIDAYS) == "2025-04-08"


def test_a_saturday_steps_only_to_monday_when_nothing_is_held():
    assert on_or_after_working_day("2025-04-05", []) == "2025-04-07"


def test_three_working_days_on_from_a_friday_is_the_next_wednesday():
    assert add_working_days("2025-04-04", 3, []) == "2025-04-09"


def test_stepping_working_days_walks_past_a_holiday():
    assert add_working_days("2025-04-04", 3, HOLIDAYS) == "2025-04-10"


def test_stepping_no_working_days_stays_where_it_is_even_on_a_saturday():
    assert add_working_days("2025-04-05", 0, HOLIDAYS) == "2025-04-05"


def test_stepping_a_negative_number_of_working_days_is_refused():
    with pytest.raises(Refused, match="negative number of working days"):
        add_working_days("2025-04-04", -1, [])


def test_a_full_week_holds_five_working_days():
    assert working_days_inclusive("2025-04-01", "2025-04-07", []) == 5


def test_a_holiday_comes_out_of_the_working_days_a_window_holds():
    assert working_days_inclusive("2025-04-01", "2025-04-07", HOLIDAYS) == 4


def test_a_window_of_one_working_day_holds_one():
    assert working_days_inclusive("2025-04-04", "2025-04-04", []) == 1


def test_a_weekend_holds_no_working_days():
    assert working_days_inclusive("2025-04-05", "2025-04-06", []) == 0
