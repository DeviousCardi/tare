"""Finding the Revenue row in force on a day."""

from dataclasses import dataclass

from tare.common.effective import all_in_force_on, in_force_on, published_on, sort_by_effective
from tare.common.types import Row


@dataclass
class Published(Row):
    effective_from: str
    letter: str = "A"
    value: int = 0


def rows() -> list[Published]:
    return [
        Published(id="p-2", effective_from="2025-04-06", letter="A", value=200),
        Published(id="p-1", effective_from="2024-04-06", letter="A", value=100),
        Published(id="p-3", effective_from="2024-04-06", letter="B", value=500),
    ]


def test_rows_read_oldest_first():
    assert [row.id for row in sort_by_effective(rows())] == ["p-1", "p-3", "p-2"]


def test_rows_taking_effect_on_one_day_fall_back_to_their_identifier():
    same = [Published(id="p-2", effective_from="2024-04-06"),
            Published(id="p-1", effective_from="2024-04-06")]
    assert [row.id for row in sort_by_effective(same)] == ["p-1", "p-2"]


def test_the_row_in_force_is_the_latest_that_had_taken_effect():
    assert in_force_on(rows(), "2025-06-01").id == "p-2"


def test_a_row_takes_effect_on_its_own_date_rather_than_the_day_after():
    assert in_force_on(rows(), "2025-04-06").id == "p-2"


def test_the_day_before_a_change_still_reads_the_older_row():
    assert in_force_on(rows(), "2025-04-05").id == "p-3"


def test_nothing_is_in_force_before_anything_was_published():
    assert in_force_on(rows(), "2020-01-01") is None


def test_nothing_is_in_force_when_nothing_was_ever_published():
    assert in_force_on([], "2025-06-01") is None


def test_every_key_gets_the_row_in_force_for_it():
    found = all_in_force_on(rows(), "2025-06-01", lambda row: row.letter)
    assert {row.letter: row.value for row in found} == {"A": 200, "B": 500}


def test_a_key_whose_row_has_not_taken_effect_yet_is_left_out():
    found = all_in_force_on(rows(), "2024-01-01", lambda row: row.letter)
    assert found == []


def test_every_key_reads_the_older_row_before_a_change():
    found = all_in_force_on(rows(), "2025-04-05", lambda row: row.letter)
    assert {row.letter: row.value for row in found} == {"A": 100, "B": 500}


def test_what_was_published_on_a_day_is_found():
    assert len(published_on(rows(), "2024-04-06")) == 2


def test_nothing_was_published_on_a_day_nothing_took_effect():
    assert published_on(rows(), "2024-04-07") == []
