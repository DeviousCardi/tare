"""The figures at which the Revenue's rules start to bite."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import BUREAU, MANAGER, build_client, build_store, headers, seed_thresholds
from tare.common.types import Threshold
from tare.modules.thresholds.rules import above, for_kind, reached, upto
from tare.modules.thresholds.schemas import ListThresholds, PublishThreshold
from tare.modules.thresholds.service import ThresholdsService


def a_store():
    store = build_store()
    seed_thresholds(store)
    return store


def service():
    return ThresholdsService(a_store())


def a_threshold(amount: int = 100000) -> Threshold:
    return Threshold(id="th-9", kind="contributions_start", frequency="monthly",
                     amount=amount, effective_from="2024-04-06")


def test_the_threshold_in_force_is_the_latest_already_taken_effect():
    assert for_kind(a_store().thresholds.all(),
                    "contributions_start", "monthly", "2025-06-01").amount == 108000


def test_a_threshold_takes_effect_on_its_own_date():
    assert for_kind(a_store().thresholds.all(),
                    "contributions_start", "monthly", "2025-04-06").amount == 108000


def test_the_day_before_a_change_still_reads_the_older_figure():
    assert for_kind(a_store().thresholds.all(),
                    "contributions_start", "monthly", "2025-04-05").amount == 104000


def test_each_frequency_carries_its_own_figure():
    assert for_kind(a_store().thresholds.all(),
                    "contributions_start", "weekly", "2025-06-01").amount == 25100


def test_a_threshold_that_never_changed_still_reads_after_the_others_did():
    assert for_kind(a_store().thresholds.all(),
                    "lower_earnings", "monthly", "2025-06-01").amount == 52300


def test_a_kind_nobody_published_is_not_in_force():
    assert for_kind(a_store().thresholds.all(), "nothing", "monthly", "2025-06-01") is None


def test_a_frequency_nobody_published_is_not_in_force():
    assert for_kind(a_store().thresholds.all(),
                    "lower_earnings", "weekly", "2025-06-01") is None


# Every figure below sits clearly on one side of the threshold or the other,
# so the answer does not depend on how a figure landing exactly on it is read.
def test_a_figure_well_above_the_threshold_has_reached_it():
    assert reached(150000, a_threshold(100000)) is True


def test_a_figure_well_below_the_threshold_has_not_reached_it():
    assert reached(50000, a_threshold(100000)) is False


def test_nothing_has_not_reached_a_threshold():
    assert reached(0, a_threshold(100000)) is False


def test_the_part_above_a_threshold_is_what_is_left_over():
    assert above(150000, a_threshold(100000)) == 50000


def test_nothing_sits_above_a_threshold_a_figure_has_not_reached():
    assert above(50000, a_threshold(100000)) == 0


def test_a_figure_exactly_on_a_threshold_has_nothing_above_it():
    assert above(100000, a_threshold(100000)) == 0


def test_the_part_up_to_a_threshold_stops_at_it():
    assert upto(150000, a_threshold(100000)) == 100000


def test_a_figure_below_a_threshold_is_all_of_it_up_to_it():
    assert upto(50000, a_threshold(100000)) == 50000


def test_the_two_parts_of_a_figure_come_back_to_the_figure():
    for amount in (0, 50000, 100000, 150000):
        row = a_threshold(100000)
        assert above(amount, row) + upto(amount, row) == amount


def test_thresholds_are_listed():
    assert service().list(MANAGER, ListThresholds())["total"] == 7


def test_a_listing_can_be_narrowed_to_one_kind():
    assert service().list(MANAGER, ListThresholds(kind="contributions_start"))["total"] == 4


def test_a_listing_can_be_narrowed_to_one_frequency():
    assert service().list(MANAGER, ListThresholds(frequency="weekly"))["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_in_force():
    assert service().list(MANAGER, ListThresholds(in_force_on="2025-06-01"))["total"] == 4


def test_a_listing_in_force_before_a_change_still_holds_every_kind():
    assert service().list(MANAGER, ListThresholds(in_force_on="2025-04-05"))["total"] == 4


def test_a_threshold_row_can_be_read():
    assert service().get(MANAGER, "th-1").amount == 104000


def test_a_threshold_nobody_published_is_missing():
    with pytest.raises(NotFound, match="threshold th-99 was not found"):
        service().get(MANAGER, "th-99")


def test_the_threshold_in_force_is_found():
    assert service().in_force("higher_levy_starts", "monthly", "2025-06-01").amount == 425000


def test_a_threshold_in_force_nowhere_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="threshold in force"):
        service().in_force("lower_earnings", "weekly", "2025-06-01")


def test_the_bureau_publishes_a_threshold():
    row = service().publish(BUREAU, PublishThreshold(
        kind="lower_earnings", frequency="weekly", amount=12000,
        effective_from="2025-04-06"))
    assert row.amount == 12000


def test_nobody_but_the_bureau_publishes_a_threshold():
    with pytest.raises(Refused, match="only the bureau may publish a threshold"):
        service().publish(MANAGER, PublishThreshold(
            kind="lower_earnings", frequency="weekly", amount=12000,
            effective_from="2025-04-06"))


def test_a_kind_the_service_does_not_hold_is_refused():
    with pytest.raises(Refused, match="is not a threshold this service holds"):
        service().publish(BUREAU, PublishThreshold(
            kind="invented", frequency="weekly", amount=1, effective_from="2025-04-06"))


def test_a_frequency_the_service_does_not_run_is_refused():
    with pytest.raises(Refused, match="is not a frequency this service runs"):
        service().publish(BUREAU, PublishThreshold(
            kind="lower_earnings", frequency="daily", amount=1,
            effective_from="2025-04-06"))


def test_one_kind_at_one_frequency_cannot_change_twice_on_a_day():
    with pytest.raises(Conflict, match="already changes on"):
        service().publish(BUREAU, PublishThreshold(
            kind="contributions_start", frequency="monthly", amount=1,
            effective_from="2025-04-06"))


def test_a_figure_is_reported_against_the_threshold_in_force():
    answer = service().against("contributions_start", "monthly", "2025-06-01", 150000)
    assert answer["threshold"] == 108000 and answer["above"] == 42000


def client():
    return build_client(a_store())


def test_the_route_lists_thresholds():
    assert client().get("/thresholds", headers=headers(MANAGER)).json()["total"] == 7


def test_the_route_reports_a_figure_against_a_threshold():
    answer = client().get(
        "/thresholds/contributions_start/against?frequency=monthly&on=2025-06-01&amount=150000",
        headers=headers(MANAGER))
    assert answer.json()["above"] == 42000


def test_the_route_answers_404_for_a_threshold_in_force_nowhere():
    answer = client().get(
        "/thresholds/lower_earnings/against?frequency=weekly&on=2025-06-01&amount=1",
        headers=headers(MANAGER))
    assert answer.status_code == 404


def test_the_route_publishes_a_threshold_and_answers_201():
    answer = client().post("/thresholds", headers=headers(BUREAU), json={
        "kind": "lower_earnings", "frequency": "weekly", "amount": 12000,
        "effective_from": "2025-04-06"})
    assert answer.status_code == 201


def test_the_route_answers_400_when_a_manager_publishes():
    answer = client().post("/thresholds", headers=headers(MANAGER), json={
        "kind": "lower_earnings", "frequency": "weekly", "amount": 12000,
        "effective_from": "2025-04-06"})
    assert answer.status_code == 400
