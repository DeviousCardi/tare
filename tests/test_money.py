"""Money is whole minor units, rounded half up, and it always balances."""

import pytest

from tare.common.errors import Refused
from tare.common.money import (
    allocate, apply_rate, apportion, format_minor, per_thousand, round_half_up, total,
)


def test_a_run_of_figures_comes_to_their_sum():
    assert total([100, 250, 5]) == 355


def test_an_empty_run_comes_to_nothing():
    assert total([]) == 0


def test_a_half_rounds_up_not_to_even():
    assert round_half_up(0.5) == 1
    assert round_half_up(1.5) == 2
    assert round_half_up(2.5) == 3


def test_a_half_below_zero_rounds_away_from_zero():
    assert round_half_up(-0.5) == -1


def test_just_under_a_half_rounds_down():
    assert round_half_up(1.49) == 1


def test_a_whole_number_rounds_to_itself():
    assert round_half_up(7) == 7


def test_a_rate_in_basis_points_is_applied():
    assert apply_rate(10000, 2000) == 2000


def test_a_rate_of_nothing_takes_nothing():
    assert apply_rate(10000, 0) == 0


def test_a_rate_rounds_half_up_rather_than_truncating():
    # 1000 at 12.5% is exactly 125; 1005 at 12.5% is 125.625 and rounds to 126.
    assert apply_rate(1005, 1250) == 126


def test_a_rate_on_a_figure_that_lands_on_a_half_rounds_up():
    # 100 at 0.5% is exactly 0.5.
    assert apply_rate(100, 50) == 1


def test_a_rate_per_thousand_is_applied():
    assert per_thousand(10000, 125) == 1250


def test_splitting_gives_every_part_its_share():
    assert allocate(900, 3) == [300, 300, 300]


def test_splitting_puts_the_odd_pennies_on_the_earliest_parts():
    assert allocate(100, 3) == [34, 33, 33]


def test_a_split_always_sums_back_to_what_was_split():
    for amount in (1, 7, 99, 100, 1001, 123456):
        for parts in (1, 2, 3, 7, 12):
            assert sum(allocate(amount, parts)) == amount


def test_splitting_a_negative_figure_keeps_it_negative_and_still_balances():
    pieces = allocate(-100, 3)
    assert sum(pieces) == -100
    assert all(piece <= 0 for piece in pieces)


def test_splitting_nothing_gives_every_part_nothing():
    assert allocate(0, 4) == [0, 0, 0, 0]


def test_splitting_into_one_part_gives_the_whole_figure():
    assert allocate(500, 1) == [500]


def test_splitting_into_no_parts_is_refused():
    with pytest.raises(Refused, match="fewer than one part"):
        allocate(100, 0)


def test_apportioning_follows_the_weights():
    assert apportion(1000, [1, 1, 2]) == [250, 250, 500]


def test_apportioning_always_sums_back_to_what_was_apportioned():
    assert sum(apportion(1000, [1, 1, 1])) == 1000
    assert sum(apportion(457, [3, 5, 11, 2])) == 457


def test_apportioning_across_equal_weights_matches_an_even_split():
    assert apportion(100, [1, 1, 1]) == allocate(100, 3)


def test_apportioning_gives_a_zero_weight_nothing():
    assert apportion(900, [1, 0, 2]) == [300, 0, 600]


def test_apportioning_across_no_weights_is_refused():
    with pytest.raises(Refused, match="across no weights"):
        apportion(100, [])


def test_apportioning_across_weights_that_come_to_nothing_is_refused():
    with pytest.raises(Refused, match="come to nothing"):
        apportion(100, [0, 0])


def test_apportioning_across_a_negative_weight_is_refused():
    with pytest.raises(Refused, match="negative weight"):
        apportion(100, [3, -1])


def test_a_figure_reads_with_two_places_and_a_separator():
    assert format_minor(123456) == "1,234.56"


def test_a_figure_under_a_pound_keeps_its_leading_zero():
    assert format_minor(5) == "0.05"


def test_a_negative_figure_reads_with_the_minus_in_front():
    assert format_minor(-2550) == "-25.50"


def test_nothing_reads_as_nothing():
    assert format_minor(0) == "0.00"
