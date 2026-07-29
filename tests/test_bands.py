"""Contribution bands, and what a figure of pay carries through them."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import BUREAU, MANAGER, build_client, build_store, headers, seed_bands
from tare.common.types import Band
from tare.modules.bands.rules import (
    band_holding,
    bands_for,
    contribution_on,
    sort_by_floor,
    width_of,
)
from tare.modules.bands.schemas import ListBands, PublishBand
from tare.modules.bands.service import BandsService


def a_store():
    store = build_store()
    seed_bands(store)
    return store


def service():
    return BandsService(a_store())


def a_band(**kw) -> Band:
    base = dict(id="bd-9", letter="A", from_pay=0, to_pay=100000,
                rate_basis_points=800, effective_from="2024-04-06")
    return Band(**{**base, **kw})


def test_bands_read_lowest_first():
    rows = sort_by_floor([a_band(from_pay=1000), a_band(from_pay=0)])
    assert [row.from_pay for row in rows] == [0, 1000]


def test_the_bands_in_force_are_the_set_published_latest():
    found = bands_for(a_store().bands.all(), "A", "2025-06-01")
    assert [row.id for row in found] == ["bd-4", "bd-5", "bd-6"]


def test_a_set_of_bands_takes_effect_on_its_own_date():
    assert bands_for(a_store().bands.all(), "A", "2025-04-06")[0].id == "bd-4"


def test_the_day_before_a_change_still_reads_the_older_set():
    assert bands_for(a_store().bands.all(), "A", "2025-04-05")[0].id == "bd-1"


def test_no_bands_are_in_force_for_a_letter_nobody_published():
    assert bands_for(a_store().bands.all(), "Z", "2025-06-01") == []


def test_no_bands_are_in_force_before_any_were_published():
    assert bands_for(a_store().bands.all(), "A", "2020-01-01") == []


def test_pay_below_a_band_puts_nothing_in_it():
    assert width_of(a_band(from_pay=1000, to_pay=2000), 500) == 0


def test_pay_inside_a_band_puts_the_part_above_its_floor_in_it():
    assert width_of(a_band(from_pay=1000, to_pay=2000), 1500) == 501


def test_pay_above_a_band_fills_it_to_its_ceiling():
    assert width_of(a_band(from_pay=1000, to_pay=2000), 5000) == 1001


def test_pay_exactly_on_a_bands_floor_puts_one_penny_in_it():
    assert width_of(a_band(from_pay=1000, to_pay=2000), 1000) == 1


def test_an_open_topped_band_takes_everything_above_its_floor():
    assert width_of(a_band(from_pay=1000, to_pay=None), 5000) == 4001


# Every figure below carries through the bands that carry a ceiling. The seeded
# top band starts at 425001, so nothing here reaches it and the answer does not
# depend on how the open-topped band is treated.
def test_pay_under_the_first_floor_carries_nothing():
    assert contribution_on(50000, bands_for(a_store().bands.all(), "A", "2025-06-01")) == 0


def test_pay_inside_the_first_band_carries_nothing_because_it_is_rated_at_nothing():
    assert contribution_on(108000, bands_for(a_store().bands.all(), "A", "2025-06-01")) == 0


def test_pay_reaching_into_the_middle_band_carries_that_bands_rate():
    # 200000 leaves 91999 above the 108001 floor plus the floor penny itself.
    bands = bands_for(a_store().bands.all(), "A", "2025-06-01")
    assert contribution_on(200000, bands) == 7360


def test_pay_filling_the_middle_band_carries_the_whole_band():
    bands = bands_for(a_store().bands.all(), "A", "2025-06-01")
    assert contribution_on(425000, bands) == 25360


def test_the_older_set_of_bands_charges_on_its_own_floors():
    bands = bands_for(a_store().bands.all(), "A", "2025-04-05")
    assert contribution_on(200000, bands) == 7680


def test_pay_of_nothing_carries_nothing():
    assert contribution_on(0, bands_for(a_store().bands.all(), "A", "2025-06-01")) == 0


def test_no_bands_at_all_carry_nothing():
    assert contribution_on(500000, []) == 0


def test_the_band_a_figure_reaches_is_the_one_its_top_penny_sits_in():
    bands = bands_for(a_store().bands.all(), "A", "2025-06-01")
    assert band_holding(200000, bands).id == "bd-5"


def test_a_figure_on_a_floor_reaches_that_band():
    bands = bands_for(a_store().bands.all(), "A", "2025-06-01")
    assert band_holding(108001, bands).id == "bd-5"


def test_a_figure_below_every_floor_reaches_the_first_band():
    bands = bands_for(a_store().bands.all(), "A", "2025-06-01")
    assert band_holding(0, bands).id == "bd-4"


def test_no_bands_means_no_band_is_reached():
    assert band_holding(1000, []) is None


def test_bands_are_listed():
    # Six for contribution letter A across two years, and four for the levy.
    assert service().list(MANAGER, ListBands())["total"] == 10


def test_a_listing_can_be_narrowed_to_the_set_in_force():
    assert service().list(MANAGER, ListBands(letter="A", in_force_on="2025-06-01"))["total"] == 3


def test_a_band_row_can_be_read():
    assert service().get(MANAGER, "bd-2").rate_basis_points == 800


def test_a_band_nobody_published_is_missing():
    with pytest.raises(NotFound, match="band bd-99 was not found"):
        service().get(MANAGER, "bd-99")


def test_the_bands_in_force_are_found():
    assert len(service().in_force("A", "2025-06-01")) == 3


def test_a_letter_in_force_nowhere_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="bands in force"):
        service().in_force("Z", "2025-06-01")


def test_the_bureau_publishes_a_band():
    row = service().publish(BUREAU, PublishBand(
        letter="B", from_pay=0, to_pay=50000, rate_basis_points=0,
        effective_from="2025-04-06"))
    assert row.letter == "B"


def test_nobody_but_the_bureau_publishes_a_band():
    with pytest.raises(Refused, match="only the bureau may publish a band"):
        service().publish(MANAGER, PublishBand(
            letter="B", from_pay=0, to_pay=50000, rate_basis_points=0,
            effective_from="2025-04-06"))


def test_a_band_cannot_end_below_where_it_starts():
    with pytest.raises(Refused, match="cannot end below where it starts"):
        service().publish(BUREAU, PublishBand(
            letter="B", from_pay=50000, to_pay=1000, rate_basis_points=0,
            effective_from="2025-04-06"))


def test_two_bands_of_one_letter_from_one_floor_on_one_day_are_refused():
    with pytest.raises(Conflict, match="already starts at"):
        service().publish(BUREAU, PublishBand(
            letter="A", from_pay=108001, to_pay=200000, rate_basis_points=900,
            effective_from="2025-04-06"))


def test_negative_pay_is_refused():
    with pytest.raises(Refused, match="pay cannot be negative"):
        service().contribution("A", "2025-06-01", -1)


def test_the_contribution_a_figure_carries_is_reported():
    assert service().contribution("A", "2025-06-01", 200000)["contribution"] == 7360


def client():
    return build_client(a_store())


def test_the_route_lists_bands():
    assert client().get("/bands", headers=headers(MANAGER)).json()["total"] == 10


def test_the_route_reports_a_contribution():
    answer = client().get("/bands/A/contribution?on=2025-06-01&pay=200000",
                          headers=headers(MANAGER))
    assert answer.json()["contribution"] == 7360


def test_the_route_answers_404_for_a_letter_in_force_nowhere():
    answer = client().get("/bands/Z/contribution?on=2025-06-01&pay=1000",
                          headers=headers(MANAGER))
    assert answer.status_code == 404


def test_the_route_publishes_a_band_and_answers_201():
    answer = client().post("/bands", headers=headers(BUREAU), json={
        "letter": "B", "from_pay": 0, "to_pay": 50000, "rate_basis_points": 0,
        "effective_from": "2025-04-06"})
    assert answer.status_code == 201


def test_the_route_refuses_a_rate_above_everything():
    answer = client().post("/bands", headers=headers(BUREAU), json={
        "letter": "B", "from_pay": 0, "to_pay": 50000, "rate_basis_points": 99999,
        "effective_from": "2025-04-06"})
    assert answer.status_code == 422
