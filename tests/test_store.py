"""The table primitive, and the one shape every listing answers with."""

from dataclasses import dataclass

import pytest

from tare.common.errors import Refused
from tare.common.paging import DEFAULT_LIMIT, MAX_LIMIT, page
from tare.common.store import Store, Table
from tare.common.types import Row


@dataclass
class Widget(Row):
    name: str
    employer_id: str = "em-1"


def table() -> Table:
    return Table("wg")


def test_a_row_put_in_can_be_found_again():
    t = table()
    row = t.insert(Widget(id="", name="one"))
    assert t.find(row.id) is row


def test_a_row_arriving_without_an_identifier_is_given_one():
    assert table().insert(Widget(id="", name="one")).id == "wg-1"


def test_identifiers_carry_the_tables_own_prefix():
    assert Table("ee").insert(Widget(id="", name="one")).id == "ee-1"


def test_identifiers_climb_as_rows_arrive():
    t = table()
    t.insert(Widget(id="", name="one"))
    assert t.insert(Widget(id="", name="two")).id == "wg-2"


def test_a_row_arriving_with_its_own_identifier_keeps_it():
    assert table().insert(Widget(id="wg-99", name="one")).id == "wg-99"


def test_a_row_nobody_put_in_is_not_found():
    assert table().find("wg-9") is None


def test_rows_read_in_the_order_they_were_put_in():
    t = table()
    t.insert(Widget(id="", name="one"))
    t.insert(Widget(id="", name="two"))
    assert [row.name for row in t.all()] == ["one", "two"]


def test_reading_every_row_hands_back_a_new_list_each_time():
    t = table()
    t.insert(Widget(id="", name="one"))
    assert t.all() is not t.all()


def test_narrowing_gives_only_the_rows_that_match():
    t = table()
    t.insert(Widget(id="", name="one"))
    t.insert(Widget(id="", name="two"))
    assert [row.name for row in t.where(lambda row: row.name == "two")] == ["two"]


def test_narrowing_on_nothing_matching_gives_an_empty_run():
    assert table().where(lambda row: True) == []


def test_the_first_match_is_the_earliest_one_put_in():
    t = table()
    t.insert(Widget(id="", name="one"))
    t.insert(Widget(id="", name="one"))
    assert t.first(lambda row: row.name == "one").id == "wg-1"


def test_there_is_no_first_match_when_nothing_matches():
    assert table().first(lambda row: True) is None


def test_a_named_field_can_be_changed_on_a_row_that_is_there():
    t = table()
    row = t.insert(Widget(id="", name="one"))
    assert t.update(row.id, name="changed").name == "changed"


def test_changing_a_field_leaves_the_others_alone():
    t = table()
    row = t.insert(Widget(id="", name="one", employer_id="em-2"))
    t.update(row.id, name="changed")
    assert row.employer_id == "em-2"


def test_a_row_taken_out_is_no_longer_found():
    t = table()
    row = t.insert(Widget(id="", name="one"))
    t.remove(row.id)
    assert t.find(row.id) is None


def test_taking_out_a_row_nobody_put_in_is_quiet():
    assert table().remove("wg-9") is None


def test_a_run_of_rows_can_be_put_in_at_once():
    t = table()
    assert len(t.insert_many([Widget(id="", name="one"), Widget(id="", name="two")])) == 2


def test_a_table_counts_the_rows_it_holds():
    t = table()
    t.insert(Widget(id="", name="one"))
    assert len(t) == 1


def test_a_table_can_be_walked_through():
    t = table()
    t.insert(Widget(id="", name="one"))
    assert [row.name for row in t] == ["one"]


def test_two_stores_do_not_share_their_rows():
    assert Store() is not Store()


def test_a_listing_answers_with_its_rows_and_a_total():
    assert page([1, 2, 3]) == {"data": [1, 2, 3], "total": 3}


def test_a_listing_of_nothing_answers_with_nothing_and_a_total_of_nothing():
    assert page([]) == {"data": [], "total": 0}


def test_a_page_holds_only_what_was_asked_for():
    assert page([1, 2, 3, 4], limit=2)["data"] == [1, 2]


def test_a_page_starts_where_it_was_asked_to():
    assert page([1, 2, 3, 4], limit=2, offset=2)["data"] == [3, 4]


def test_the_total_counts_the_whole_match_and_not_the_page():
    assert page([1, 2, 3, 4], limit=2)["total"] == 4


def test_a_page_past_the_end_is_empty_but_the_total_still_counts():
    assert page([1, 2, 3], offset=10) == {"data": [], "total": 3}


def test_a_listing_asked_for_nothing_hands_back_nothing_and_still_counts():
    assert page([1, 2, 3], limit=0) == {"data": [], "total": 3}


def test_a_listing_that_is_not_told_a_limit_takes_the_default():
    assert len(page(list(range(200)))["data"]) == DEFAULT_LIMIT


def test_a_negative_offset_is_refused():
    with pytest.raises(Refused, match="offset cannot be negative"):
        page([1], offset=-1)


def test_a_negative_limit_is_refused():
    with pytest.raises(Refused, match="limit cannot be negative"):
        page([1], limit=-1)


def test_a_limit_past_what_the_service_will_serve_is_refused():
    with pytest.raises(Refused, match="cannot be more than"):
        page([1], limit=MAX_LIMIT + 1)
