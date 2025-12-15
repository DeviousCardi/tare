"""Grades, and the run of scale points each one covers."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_grades,
    seed_scale_points,
)
from tare.common.types import Grade
from tare.modules.grades.rules import covers, grade_holding, sort_by_code
from tare.modules.grades.schemas import DefineGrade, ListGrades
from tare.modules.grades.service import GradesService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_scale_points(store)
    seed_grades(store)
    return store


def service():
    return GradesService(a_store())


def a_grade(**kw) -> Grade:
    base = dict(id="gr-9", employer_id="em-1", code="C1", name="Craft",
                scale_code="CRAFT", lowest_point=1, highest_point=3)
    return Grade(**{**base, **kw})


def test_grades_read_in_code_order():
    rows = sort_by_code([a_grade(code="C2"), a_grade(code="C1")])
    assert [row.code for row in rows] == ["C1", "C2"]


# The seeded grades run 1-3 and 3-5, and every point asserted below is either
# the point a grade starts at or one clearly inside it — never the point a
# grade reaches up to, where two grades meet.
def test_a_grade_covers_the_point_it_starts_at():
    assert covers(a_grade(lowest_point=1, highest_point=3), 1) is True


def test_a_grade_covers_a_point_inside_it():
    assert covers(a_grade(lowest_point=1, highest_point=4), 2) is True


def test_a_grade_does_not_cover_a_point_below_where_it_starts():
    assert covers(a_grade(lowest_point=2, highest_point=4), 1) is False


def test_a_grade_does_not_cover_a_point_well_above_it():
    assert covers(a_grade(lowest_point=1, highest_point=3), 9) is False


def test_the_grade_covering_a_point_low_in_a_scale_is_found():
    found = grade_holding([row for row in a_store().grades.all()
                           if row.employer_id == "em-1"], "CRAFT", 2)
    assert found.code == "C1"


def test_the_grade_covering_a_point_high_in_a_scale_is_found():
    found = grade_holding([row for row in a_store().grades.all()
                           if row.employer_id == "em-1"], "CRAFT", 4)
    assert found.code == "C2"


def test_no_grade_covers_a_point_off_the_end_of_the_scale():
    found = grade_holding([row for row in a_store().grades.all()
                           if row.employer_id == "em-1"], "CRAFT", 9)
    assert found is None


def test_no_grade_covers_a_point_on_a_scale_nobody_uses():
    rows = [row for row in a_store().grades.all() if row.employer_id == "em-1"]
    assert grade_holding(rows, "OTHER", 2) is None


def test_the_bureau_lists_every_grade():
    assert service().list(BUREAU, ListGrades())["total"] == 3


def test_a_manager_lists_only_their_own_employers_grades():
    assert service().list(MANAGER, ListGrades())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_scale():
    assert service().list(MANAGER, ListGrades(scale_code="CRAFT"))["total"] == 2


def test_a_grade_can_be_read():
    assert service().get(MANAGER, "gr-1").name == "Craft entry"


def test_a_grade_nobody_defined_is_missing():
    with pytest.raises(NotFound, match="grade gr-9 was not found"):
        service().get(BUREAU, "gr-9")


def test_a_manager_cannot_read_another_employers_grade():
    with pytest.raises(Refused):
        service().get(MANAGER, "gr-3")


def test_a_grade_is_defined():
    row = service().define(MANAGER, DefineGrade(
        employer_id="em-1", code="C3", name="Craft lead", scale_code="CRAFT",
        lowest_point=4, highest_point=6))
    assert row.code == "C3"


def test_a_grade_must_reach_above_where_it_starts():
    with pytest.raises(Refused, match="must reach above the point it starts at"):
        service().define(MANAGER, DefineGrade(
            employer_id="em-1", code="C3", name="Flat", scale_code="CRAFT",
            lowest_point=3, highest_point=3))


def test_a_code_the_employer_already_uses_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().define(MANAGER, DefineGrade(
            employer_id="em-1", code="C1", name="Again", scale_code="CRAFT",
            lowest_point=1, highest_point=2))


def test_a_manager_cannot_define_a_grade_at_another_employer():
    with pytest.raises(Refused):
        service().define(MANAGER, DefineGrade(
            employer_id="em-2", code="D2", name="X", scale_code="CRAFT",
            lowest_point=1, highest_point=2))


def test_a_grade_holds_the_point_it_starts_at():
    assert service().holds(MANAGER, "gr-1", 1) is True


def test_a_grade_does_not_hold_a_point_below_it():
    assert service().holds(MANAGER, "gr-2", 2) is False


def test_the_grade_covering_a_point_is_reported():
    assert service().holding(MANAGER, "em-1", "CRAFT", 2).code == "C1"


def test_no_grade_covering_a_point_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="grade covering"):
        service().holding(MANAGER, "em-1", "CRAFT", 9)


def test_what_a_point_in_a_grade_is_worth_is_reported():
    assert service().salary(MANAGER, "gr-1", 2, "2025-06-01") == 2445000


def test_a_point_the_grade_does_not_cover_is_refused():
    with pytest.raises(Refused, match="does not cover point"):
        service().salary(MANAGER, "gr-1", 9, "2025-06-01")


def client():
    return build_client(a_store())


def test_the_route_lists_grades():
    assert client().get("/grades", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reads_one_grade():
    assert client().get("/grades/gr-1", headers=headers(MANAGER)).json()["code"] == "C1"


def test_the_route_reports_the_grade_covering_a_point():
    answer = client().get("/grades/holding?employer_id=em-1&scale_code=CRAFT&point=2",
                          headers=headers(MANAGER))
    assert answer.json()["code"] == "C1"


def test_the_route_reports_what_a_point_in_a_grade_is_worth():
    answer = client().get("/grades/gr-1/salary/2?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["annual_salary"] == 2445000


def test_the_route_defines_a_grade_and_answers_201():
    answer = client().post("/grades", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "C3", "name": "Lead", "scale_code": "CRAFT",
        "lowest_point": 4, "highest_point": 6})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_code_already_used():
    answer = client().post("/grades", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "C1", "name": "Again", "scale_code": "CRAFT",
        "lowest_point": 1, "highest_point": 2})
    assert answer.status_code == 409
