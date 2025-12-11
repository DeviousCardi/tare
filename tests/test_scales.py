"""Pay scales, their points, and what a backdated award leaves owing."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import BUREAU, MANAGER, build_client, build_store, headers, seed_scale_points
from tare.modules.scales.rules import arrears_for, points_of, sort_by_point, step_up, value_at
from tare.modules.scales.schemas import ListScalePoints, PublishScalePoint
from tare.modules.scales.service import ScalesService


def a_store():
    store = build_store()
    seed_scale_points(store)
    return store


def service():
    return ScalesService(a_store())


def rows():
    return a_store().scale_points.all()


def test_points_read_lowest_first():
    ordered = sort_by_point(points_of(rows(), "CRAFT", "2025-06-01"))
    assert [row.point for row in ordered] == [1, 2, 3, 4]


def test_the_scale_in_force_is_the_one_published_latest():
    assert points_of(rows(), "CRAFT", "2025-06-01")[0].annual_salary == 2263500


def test_a_scale_takes_effect_on_its_own_date():
    assert points_of(rows(), "CRAFT", "2025-04-06")[0].annual_salary == 2263500


def test_the_day_before_a_change_still_reads_the_older_scale():
    assert points_of(rows(), "CRAFT", "2025-04-05")[0].annual_salary == 2190000


def test_a_scale_nobody_published_has_no_points():
    assert points_of(rows(), "NONE", "2025-06-01") == []


def test_a_point_is_worth_what_the_scale_in_force_says():
    assert value_at(rows(), "CRAFT", 3, "2025-06-01") == 2628500


def test_a_point_before_the_scale_was_published_is_worth_nothing_known():
    assert value_at(rows(), "CRAFT", 3, "2020-01-01") is None


def test_a_point_nobody_published_is_worth_nothing_known():
    assert value_at(rows(), "CRAFT", 9, "2025-06-01") is None


def test_the_next_point_up_is_found():
    assert step_up(rows(), "CRAFT", 2, "2025-06-01") == 3


def test_the_top_of_a_scale_has_nothing_above_it():
    assert step_up(rows(), "CRAFT", 4, "2025-06-01") is None


# 73, 146 and 365 all divide the year exactly at this uplift, so no fraction of
# a penny is ever left over and the answer does not depend on how one is
# treated.
def test_a_full_year_of_an_uplift_is_worth_the_whole_difference():
    assert arrears_for(2190000, 2263500, 365) == 73500


def test_a_fifth_of_a_year_is_worth_a_fifth_of_the_difference():
    assert arrears_for(2190000, 2263500, 73) == 14700


def test_two_fifths_of_a_year_is_worth_two_fifths_of_the_difference():
    assert arrears_for(2190000, 2263500, 146) == 29400


def test_no_days_are_owed_nothing():
    assert arrears_for(2190000, 2263500, 0) == 0


def test_a_negative_run_of_days_is_owed_nothing():
    assert arrears_for(2190000, 2263500, -10) == 0


def test_a_point_worth_no_more_than_before_owes_nothing():
    assert arrears_for(2263500, 2263500, 365) == 0


def test_a_point_worth_less_than_before_owes_nothing():
    assert arrears_for(2263500, 2190000, 365) == 0


def test_points_are_listed():
    assert service().list(MANAGER, ListScalePoints())["total"] == 8


def test_a_listing_can_be_narrowed_to_the_scale_in_force():
    answer = service().list(MANAGER, ListScalePoints(scale_code="CRAFT", in_force_on="2025-06-01"))
    assert answer["total"] == 4


def test_a_point_row_can_be_read():
    assert service().get(MANAGER, "sp-1").annual_salary == 2190000


def test_a_point_nobody_published_is_missing():
    with pytest.raises(NotFound, match="scale point sp-99 was not found"):
        service().get(MANAGER, "sp-99")


def test_what_a_point_is_worth_is_reported():
    assert service().value("CRAFT", 1, "2025-06-01") == 2263500


def test_a_point_in_force_nowhere_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="scale point in force"):
        service().value("CRAFT", 9, "2025-06-01")


def test_the_bureau_publishes_a_point():
    row = service().publish(BUREAU, PublishScalePoint(
        scale_code="CRAFT", point=5, annual_salary=2992500, effective_from="2025-04-06"))
    assert row.point == 5


def test_nobody_but_the_bureau_publishes_a_point():
    with pytest.raises(Refused, match="only the bureau may publish a scale point"):
        service().publish(MANAGER, PublishScalePoint(
            scale_code="CRAFT", point=5, annual_salary=1, effective_from="2025-04-06"))


def test_one_point_cannot_change_twice_on_a_day():
    with pytest.raises(Conflict, match="already changes on"):
        service().publish(BUREAU, PublishScalePoint(
            scale_code="CRAFT", point=1, annual_salary=1, effective_from="2025-04-06"))


def test_a_published_point_extends_the_scale():
    svc = service()
    svc.publish(BUREAU, PublishScalePoint(
        scale_code="CRAFT", point=5, annual_salary=2992500, effective_from="2025-04-06"))
    assert svc.next_point("CRAFT", 4, "2025-06-01") == 5


def test_what_a_backdated_award_leaves_owing_is_reported():
    answer = service().arrears("CRAFT", 1, "2025-04-05", "2025-06-01", 365)
    assert answer["was"] == 2190000 and answer["arrears"] == 73500


def test_a_negative_run_of_days_is_refused():
    with pytest.raises(Refused, match="cannot be negative"):
        service().arrears("CRAFT", 1, "2025-04-05", "2025-06-01", -1)


def client():
    return build_client(a_store())


def test_the_route_lists_points():
    assert client().get("/scales", headers=headers(MANAGER)).json()["total"] == 8


def test_the_route_reports_what_a_point_is_worth():
    answer = client().get("/scales/CRAFT/point/2?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["annual_salary"] == 2445000


def test_the_route_reports_the_next_point_up():
    answer = client().get("/scales/CRAFT/point/2?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["next_point"] == 3


def test_the_route_reports_what_an_award_leaves_owing():
    answer = client().get(
        "/scales/CRAFT/arrears/1?was_on=2025-04-05&now_on=2025-06-01&days=365",
        headers=headers(MANAGER))
    assert answer.json()["arrears"] == 73500


def test_the_route_publishes_a_point_and_answers_201():
    answer = client().post("/scales", headers=headers(BUREAU), json={
        "scale_code": "CRAFT", "point": 5, "annual_salary": 2992500,
        "effective_from": "2025-04-06"})
    assert answer.status_code == 201
