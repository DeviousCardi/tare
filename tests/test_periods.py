"""Windows, what they cover, how they cut and how a figure spreads over them."""

import pytest

from tare.common.errors import Refused
from tare.common.periods import (
    Window, common_days, covers, days_in, split_at, touches, weighted,
)

APRIL = Window("2025-04-01", "2025-04-30")


def test_a_window_counts_both_of_its_ends():
    assert days_in(APRIL) == 30


def test_a_window_of_a_single_day_covers_one_day():
    assert days_in(Window("2025-04-04", "2025-04-04")) == 1


def test_a_window_that_ends_before_it_starts_cannot_be_made():
    with pytest.raises(Refused, match="ends before it starts"):
        Window("2025-04-30", "2025-04-01")


def test_the_first_day_of_a_window_is_covered():
    assert covers(APRIL, "2025-04-01") is True


def test_the_last_day_of_a_window_is_covered():
    assert covers(APRIL, "2025-04-30") is True


def test_the_day_after_a_window_is_not_covered():
    assert covers(APRIL, "2025-05-01") is False


def test_two_windows_sharing_a_day_touch():
    assert touches(APRIL, Window("2025-04-30", "2025-05-10")) is True


def test_two_windows_that_do_not_meet_do_not_touch():
    assert touches(APRIL, Window("2025-05-01", "2025-05-10")) is False


def test_windows_that_do_not_meet_share_no_days():
    assert common_days(APRIL, Window("2025-05-01", "2025-05-10")) == 0


def test_windows_that_share_one_day_share_one_day():
    assert common_days(APRIL, Window("2025-04-30", "2025-05-10")) == 1


def test_a_window_inside_another_shares_all_of_its_own_days():
    assert common_days(APRIL, Window("2025-04-10", "2025-04-14")) == 5


def test_a_window_shares_every_day_with_itself():
    assert common_days(APRIL, APRIL) == 30


def test_a_cut_puts_the_named_day_at_the_start_of_the_later_part():
    before, after = split_at(APRIL, "2025-04-16")
    assert after.start == "2025-04-16"


def test_a_cut_ends_the_earlier_part_the_day_before():
    before, after = split_at(APRIL, "2025-04-16")
    assert before.end == "2025-04-15"


def test_the_two_parts_of_a_cut_still_cover_the_whole_window():
    before, after = split_at(APRIL, "2025-04-16")
    assert days_in(before) + days_in(after) == days_in(APRIL)


def test_cutting_outside_the_window_is_refused():
    with pytest.raises(Refused, match="is not inside window"):
        split_at(APRIL, "2025-05-02")


def test_cutting_on_the_first_day_is_refused_rather_than_leaving_nothing():
    with pytest.raises(Refused, match="would leave nothing before it"):
        split_at(APRIL, "2025-04-01")


def test_cutting_on_the_last_day_leaves_that_day_as_the_later_part():
    before, after = split_at(APRIL, "2025-04-30")
    assert days_in(after) == 1


def test_a_figure_spreads_across_windows_by_the_days_they_cover():
    halves = [Window("2025-04-01", "2025-04-15"), Window("2025-04-16", "2025-04-30")]
    assert weighted(3000, halves) == [1500, 1500]


def test_a_spread_always_sums_back_to_the_figure_it_split():
    parts = [Window("2025-04-01", "2025-04-10"), Window("2025-04-11", "2025-04-30")]
    assert sum(weighted(1001, parts)) == 1001


def test_a_longer_window_takes_the_larger_share():
    parts = [Window("2025-04-01", "2025-04-10"), Window("2025-04-11", "2025-04-30")]
    spread = weighted(3000, parts)
    assert spread[1] > spread[0]


def test_a_figure_spread_over_one_window_lands_on_it_whole():
    assert weighted(1234, [APRIL]) == [1234]


def test_spreading_across_no_windows_is_refused():
    with pytest.raises(Refused, match="across no windows"):
        weighted(100, [])
