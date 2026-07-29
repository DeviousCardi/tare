"""The posts people hold, and where their cost belongs."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_cost_centres,
    seed_departments, seed_employees, seed_employers, seed_positions,
)
from tare.common.types import Position
from tare.modules.positions.rules import (
    headcount, held_by, held_on, in_cost_centre, sort_by_held_from,
)
from tare.modules.positions.schemas import AppointToPosition, EndPosition, ListPositions
from tare.modules.positions.service import PositionsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_departments(store)
    seed_cost_centres(store)
    seed_positions(store)
    return store


def service():
    return PositionsService(a_store())


def a_post(**kw) -> Position:
    base = dict(id="ps-9", employee_id="ee-1", employer_id="em-1", department_id="dp-1",
                cost_centre_id="cc-1", title="Hand", held_from="2024-01-01", held_to=None)
    return Position(**{**base, **kw})


def test_posts_read_earliest_first():
    rows = sort_by_held_from([a_post(held_from="2024-06-01"), a_post(held_from="2024-01-01")])
    assert [row.held_from for row in rows] == ["2024-01-01", "2024-06-01"]


def test_a_post_is_held_on_the_day_it_started():
    assert held_on(a_post(held_from="2024-01-01"), "2024-01-01") is True


def test_a_post_is_not_held_the_day_before_it_started():
    assert held_on(a_post(held_from="2024-01-01"), "2023-12-31") is False


def test_a_post_is_still_held_on_the_day_it_ended():
    assert held_on(a_post(held_from="2024-01-01", held_to="2024-06-30"), "2024-06-30") is True


def test_a_post_is_not_held_the_day_after_it_ended():
    assert held_on(a_post(held_from="2024-01-01", held_to="2024-06-30"), "2024-07-01") is False


def test_the_post_somebody_held_is_found():
    assert held_by(a_store().positions.all(), "ee-1", "2025-06-01").id == "ps-1"


def test_a_post_that_has_ended_is_no_longer_held():
    assert held_by(a_store().positions.all(), "ee-3", "2025-08-01") is None


def test_the_latest_appointment_wins_where_two_cover_a_day():
    rows = [a_post(id="a", held_from="2024-01-01"), a_post(id="b", held_from="2024-07-01")]
    assert held_by(rows, "ee-1", "2024-08-01").id == "b"


def test_the_posts_booked_to_a_centre_are_found():
    assert len(in_cost_centre(a_store().positions.all(), "cc-2", "2025-08-01")) == 1


def test_a_centre_with_nothing_booked_to_it_on_a_day_has_none():
    assert in_cost_centre(a_store().positions.all(), "cc-3", "2025-08-01") == []


def test_a_departments_headcount_counts_who_held_a_post():
    assert headcount(a_store().positions.all(), "dp-1", "2025-08-01") == 1


def test_a_headcount_leaves_out_a_post_that_had_ended():
    assert headcount(a_store().positions.all(), "dp-3", "2025-08-01") == 0


def test_a_headcount_counts_each_person_once():
    rows = [a_post(id="a", employee_id="ee-1"), a_post(id="b", employee_id="ee-1")]
    assert headcount(rows, "dp-1", "2024-06-01") == 1


def test_the_bureau_lists_every_post():
    assert service().list(BUREAU, ListPositions())["total"] == 4


def test_a_manager_lists_only_their_own_employers_posts():
    assert service().list(MANAGER, ListPositions())["total"] == 3


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListPositions(employee_id="ee-1"))["total"] == 1


def test_a_listing_can_be_narrowed_to_a_centre():
    assert service().list(MANAGER, ListPositions(cost_centre_id="cc-2"))["total"] == 2


def test_a_listing_can_be_narrowed_to_a_day():
    assert service().list(BUREAU, ListPositions(held_on="2025-08-01"))["total"] == 3


def test_a_post_can_be_read():
    assert service().get(MANAGER, "ps-1").title == "Bench joiner"


def test_a_post_nobody_made_is_missing():
    with pytest.raises(NotFound, match="position ps-9 was not found"):
        service().get(BUREAU, "ps-9")


def test_a_manager_cannot_read_another_employers_post():
    with pytest.raises(Refused):
        service().get(MANAGER, "ps-4")


def test_the_post_somebody_holds_is_reported():
    assert service().held(MANAGER, "ee-1", "2025-06-01").id == "ps-1"


def test_holding_no_post_on_a_day_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="position held"):
        service().held(MANAGER, "ee-3", "2025-08-01")


def test_somebody_is_appointed_to_a_post():
    row = service().appoint(MANAGER, AppointToPosition(
        employee_id="ee-3", department_id="dp-1", cost_centre_id="cc-2",
        title="Clerk", held_from="2025-08-01"))
    assert row.employer_id == "em-1"


def test_a_post_cannot_start_before_the_person_joined():
    with pytest.raises(Refused, match="before the person joined"):
        service().appoint(MANAGER, AppointToPosition(
            employee_id="ee-2", department_id="dp-1", cost_centre_id="cc-2",
            title="Hand", held_from="2024-01-01"))


def test_a_post_over_one_already_held_is_refused():
    with pytest.raises(Conflict, match="already holds a post"):
        service().appoint(MANAGER, AppointToPosition(
            employee_id="ee-1", department_id="dp-1", cost_centre_id="cc-2",
            title="Hand", held_from="2025-06-01"))


def test_a_post_cannot_be_booked_to_a_closed_centre():
    with pytest.raises(Refused, match="is closed and cannot take a post"):
        service().appoint(MANAGER, AppointToPosition(
            employee_id="ee-3", department_id="dp-1", cost_centre_id="cc-3",
            title="Clerk", held_from="2025-08-01"))


def test_a_post_must_sit_in_the_persons_own_employer():
    with pytest.raises(Refused, match="person's own employer"):
        service().appoint(BUREAU, AppointToPosition(
            employee_id="ee-3", department_id="dp-4", cost_centre_id="cc-2",
            title="Clerk", held_from="2025-08-01"))


def test_a_post_is_ended():
    assert service().end(MANAGER, "ps-1", EndPosition(held_to="2025-09-30")).held_to == "2025-09-30"


def test_a_post_cannot_end_twice():
    with pytest.raises(Conflict, match="already ended"):
        service().end(MANAGER, "ps-3", EndPosition(held_to="2025-09-30"))


def test_a_post_cannot_end_before_it_started():
    with pytest.raises(Refused, match="end before it started"):
        service().end(MANAGER, "ps-1", EndPosition(held_to="2019-01-01"))


def test_a_departments_headcount_is_reported():
    assert service().headcount(MANAGER, "dp-2", "2025-08-01") == 1


def client():
    return build_client(a_store())


def test_the_route_lists_posts():
    assert client().get("/positions", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reads_one_post():
    assert client() \
        .get("/positions/ps-1", headers=headers(MANAGER)).json()["title"] == "Bench joiner"


def test_the_route_reports_a_headcount():
    answer = client().get("/positions/headcount/dp-2?on=2025-08-01", headers=headers(MANAGER))
    assert answer.json()["headcount"] == 1


def test_the_route_appoints_somebody_and_answers_201():
    answer = client().post("/positions", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "department_id": "dp-1", "cost_centre_id": "cc-2",
        "title": "Clerk", "held_from": "2025-08-01"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_post_over_one_already_held():
    answer = client().post("/positions", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "department_id": "dp-1", "cost_centre_id": "cc-2",
        "title": "Hand", "held_from": "2025-06-01"})
    assert answer.status_code == 409


def test_the_route_ends_a_post():
    answer = client().post("/positions/ps-1/end", headers=headers(MANAGER),
                           json={"held_to": "2025-09-30"})
    assert answer.json()["held_to"] == "2025-09-30"
