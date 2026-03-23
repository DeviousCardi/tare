"""Journeys: trips made in somebody's own car, and what the miles are worth."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_journeys,
)
from tare.common.types import Journey
from tare.modules.journeys.rules import (
    HIGHER_RATE, approved_only, between, miles_in, sort_by_travelled, worth_of,
)
from tare.modules.journeys.schemas import ApproveJourney, ListJourneys, RecordJourney
from tare.modules.journeys.service import JourneysService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_journeys):
        seed(store)
    return store


def service():
    return JourneysService(a_store())


def a_journey(**kw) -> Journey:
    base = dict(id="jn-9", employee_id="ee-1", employer_id="em-1",
                travelled_on="2025-06-02", miles=120, reason="Site visit",
                approved=True)
    return Journey(**{**base, **kw})


def test_journeys_read_earliest_first():
    rows = sort_by_travelled([a_journey(travelled_on="2025-07-01"),
                              a_journey(travelled_on="2025-06-02")])
    assert [row.travelled_on for row in rows] == ["2025-06-02", "2025-07-01"]


def test_only_approved_journeys_survive_the_narrowing():
    rows = approved_only([a_journey(id="a"), a_journey(id="b", approved=False)])
    assert [row.id for row in rows] == ["a"]


def test_a_window_takes_a_journey_on_its_first_day():
    mine = [row for row in a_store().journeys.all() if row.employee_id == "ee-1"]
    assert len(between(mine, "2025-06-02", "2025-06-02")) == 1


def test_a_window_leaves_out_a_journey_outside_it():
    mine = [row for row in a_store().journeys.all() if row.employee_id == "ee-1"]
    assert between(mine, "2025-01-01", "2025-01-31") == []


def test_approved_miles_across_a_window_are_added_up():
    mine = [row for row in a_store().journeys.all() if row.employee_id == "ee-1"]
    assert miles_in(mine, "2025-06-01", "2025-06-30") == 200


def test_a_journey_still_waiting_on_approval_is_not_counted():
    mine = [row for row in a_store().journeys.all() if row.employee_id == "ee-1"]
    assert miles_in(mine, "2025-07-01", "2025-07-31") == 0


# Every run of miles below stays well inside the stretch the higher rate covers,
# so what it is worth does not depend on how a run that crosses the end of that
# stretch is treated.
def test_a_run_of_miles_is_worth_the_higher_rate():
    assert worth_of(200, 0) == 200 * HIGHER_RATE


def test_one_mile_is_worth_the_higher_rate():
    assert worth_of(1, 0) == HIGHER_RATE


def test_miles_part_way_through_the_stretch_are_still_the_higher_rate():
    assert worth_of(500, 4000) == 500 * HIGHER_RATE


def test_no_miles_are_worth_nothing():
    assert worth_of(0, 0) == 0


def test_a_negative_run_of_miles_is_worth_nothing():
    assert worth_of(-10, 0) == 0


def test_the_bureau_lists_every_journey():
    assert service().list(BUREAU, ListJourneys())["total"] == 4


def test_a_manager_lists_only_their_own_employers_journeys():
    assert service().list(MANAGER, ListJourneys())["total"] == 3


def test_a_listing_can_be_narrowed_to_what_is_approved():
    assert service().list(MANAGER, ListJourneys(approved_only=True))["total"] == 2


def test_a_journey_can_be_read():
    assert service().get(MANAGER, "jn-1").miles == 120


def test_a_journey_nobody_recorded_is_missing():
    with pytest.raises(NotFound, match="journey jn-9 was not found"):
        service().get(BUREAU, "jn-9")


def test_a_manager_cannot_read_another_employers_journey():
    with pytest.raises(Refused):
        service().get(MANAGER, "jn-4")


def test_a_journey_is_recorded_and_waits_on_approval():
    row = service().record(MANAGER, RecordJourney(
        employee_id="ee-1", travelled_on="2025-08-01", miles=60, reason="Site"))
    assert row.approved is False


def test_a_journey_cannot_be_recorded_for_a_day_somebody_was_not_in_post():
    with pytest.raises(Refused, match="was not in post on"):
        service().record(MANAGER, RecordJourney(
            employee_id="ee-3", travelled_on="2025-08-01", miles=60, reason="Site"))


def test_a_journey_is_approved():
    assert service().approve(MANAGER, "jn-3", ApproveJourney()).approved is True


def test_a_journey_already_approved_cannot_be_approved_again():
    with pytest.raises(Conflict, match="already in the state"):
        service().approve(MANAGER, "jn-1", ApproveJourney())


def test_approving_a_journey_brings_its_miles_into_the_total():
    svc = service()
    svc.approve(MANAGER, "jn-3", ApproveJourney())
    assert svc.mileage(MANAGER, "ee-1", "2025-01-01", "2025-12-31")["miles"] == 240


def test_the_mileage_across_a_window_is_reported_with_what_it_is_worth():
    answer = service().mileage(MANAGER, "ee-1", "2025-06-01", "2025-06-30")
    assert answer["miles"] == 200 and answer["worth"] == 9000


def client():
    return build_client(a_store())


def test_the_route_lists_journeys():
    assert client().get("/journeys", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reports_mileage():
    answer = client().get("/journeys/mileage/ee-1?start=2025-06-01&end=2025-06-30",
                          headers=headers(MANAGER))
    assert answer.json()["worth"] == 9000


def test_the_route_records_a_journey_and_answers_201():
    answer = client().post("/journeys", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "travelled_on": "2025-08-01", "miles": 60,
        "reason": "Site"})
    assert answer.status_code == 201


def test_the_route_approves_a_journey():
    answer = client().post("/journeys/jn-3/approve", headers=headers(MANAGER),
                           json={"approved": True})
    assert answer.json()["approved"] is True


def test_the_route_refuses_a_journey_longer_than_anybody_drives_in_a_day():
    answer = client().post("/journeys", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "travelled_on": "2025-08-01", "miles": 5000,
        "reason": "Site"})
    assert answer.status_code == 422
