"""The parts an employer's organisation is divided into."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_departments, seed_employers,
)
from tare.common.types import Department
from tare.modules.departments.rules import (
    ancestors_of, children_of, depth_of, sort_by_code, would_make_a_cycle,
)
from tare.modules.departments.schemas import ListDepartments, MoveDepartment, OpenDepartment
from tare.modules.departments.service import DepartmentsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_departments(store)
    return store


def service():
    return DepartmentsService(a_store())


def rows():
    return a_store().departments.all()


def test_departments_read_in_code_order():
    ordered = sort_by_code([Department(id="a", employer_id="em-1", code="B", name="b", parent_id=None),
                            Department(id="b", employer_id="em-1", code="A", name="a", parent_id=None)])
    assert [row.code for row in ordered] == ["A", "B"]


def test_the_children_of_a_department_are_found():
    assert [row.id for row in children_of(rows(), "dp-1")] == ["dp-2"]


def test_a_department_with_nothing_under_it_has_no_children():
    assert children_of(rows(), "dp-2") == []


def test_the_departments_at_the_top_have_no_parent():
    assert len(children_of(rows(), None)) == 3


def test_the_ancestors_of_a_department_are_found_nearest_first():
    assert [row.id for row in ancestors_of(rows(), "dp-2")] == ["dp-1"]


def test_a_department_at_the_top_has_no_ancestors():
    assert ancestors_of(rows(), "dp-1") == []


def test_depth_counts_how_far_down_a_department_sits():
    assert depth_of(rows(), "dp-2") == 1


def test_a_department_at_the_top_is_nothing_deep():
    assert depth_of(rows(), "dp-1") == 0


def test_a_department_cannot_sit_under_itself():
    assert would_make_a_cycle(rows(), "dp-1", "dp-1") is True


def test_a_department_cannot_sit_under_its_own_child():
    assert would_make_a_cycle(rows(), "dp-1", "dp-2") is True


def test_a_department_may_sit_under_an_unrelated_one():
    assert would_make_a_cycle(rows(), "dp-3", "dp-1") is False


def test_a_cycle_already_in_the_data_is_reported_rather_than_hanging():
    looped = [Department(id="a", employer_id="em-1", code="A", name="a", parent_id="b"),
              Department(id="b", employer_id="em-1", code="B", name="b", parent_id="a")]
    assert len(ancestors_of(looped, "a")) <= 2


def test_the_bureau_lists_every_department():
    assert service().list(BUREAU, ListDepartments())["total"] == 4


def test_a_manager_lists_only_their_own_employers_departments():
    assert service().list(MANAGER, ListDepartments())["total"] == 3


def test_a_listing_can_be_narrowed_to_one_employer():
    assert service().list(BUREAU, ListDepartments(employer_id="em-2"))["total"] == 1


def test_a_listing_can_be_narrowed_to_what_sits_under_a_department():
    assert service().list(MANAGER, ListDepartments(parent_id="dp-1"))["total"] == 1


def test_a_department_can_be_read():
    assert service().get(MANAGER, "dp-1").name == "Operations"


def test_a_department_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="department dp-9 was not found"):
        service().get(BUREAU, "dp-9")


def test_a_manager_cannot_read_another_employers_department():
    with pytest.raises(Refused):
        service().get(MANAGER, "dp-4")


def test_a_department_is_opened():
    row = service().open(MANAGER, OpenDepartment(
        employer_id="em-1", code="FIN", name="Finance"))
    assert row.code == "FIN" and row.parent_id is None


def test_a_department_can_be_opened_under_another():
    row = service().open(MANAGER, OpenDepartment(
        employer_id="em-1", code="FIN", name="Finance", parent_id="dp-1"))
    assert row.parent_id == "dp-1"


def test_a_code_the_employer_already_uses_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().open(MANAGER, OpenDepartment(
            employer_id="em-1", code="OPS", name="Again"))


def test_the_same_code_at_another_employer_is_allowed():
    assert service().open(BUREAU, OpenDepartment(
        employer_id="em-2", code="OPS", name="Operations")).code == "OPS"


def test_a_department_cannot_be_opened_under_another_employers():
    with pytest.raises(Refused, match="another employer's"):
        service().open(BUREAU, OpenDepartment(
            employer_id="em-2", code="FIN", name="Finance", parent_id="dp-1"))


def test_a_manager_cannot_open_a_department_at_another_employer():
    with pytest.raises(Refused):
        service().open(MANAGER, OpenDepartment(
            employer_id="em-2", code="FIN", name="Finance"))


def test_a_department_is_moved_under_another():
    assert service().move(MANAGER, "dp-3", MoveDepartment(parent_id="dp-1")).parent_id == "dp-1"


def test_a_department_is_moved_back_to_the_top():
    assert service().move(MANAGER, "dp-2", MoveDepartment(parent_id=None)).parent_id is None


def test_moving_a_department_under_its_own_child_is_refused():
    with pytest.raises(Refused, match="fold the organisation onto itself"):
        service().move(MANAGER, "dp-1", MoveDepartment(parent_id="dp-2"))


def test_moving_a_department_under_itself_is_refused():
    with pytest.raises(Refused, match="fold the organisation onto itself"):
        service().move(MANAGER, "dp-1", MoveDepartment(parent_id="dp-1"))


def test_moving_a_department_under_another_employers_is_refused():
    with pytest.raises(Refused, match="another employer's"):
        service().move(BUREAU, "dp-4", MoveDepartment(parent_id="dp-1"))


def client():
    return build_client(a_store())


def test_the_route_lists_departments():
    assert client().get("/departments", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reads_one_department():
    assert client().get("/departments/dp-1", headers=headers(MANAGER)).json()["code"] == "OPS"


def test_the_route_reports_what_sits_under_a_department():
    answer = client().get("/departments/dp-1/children", headers=headers(MANAGER))
    assert answer.json()["total"] == 1


def test_the_route_reports_what_a_department_sits_under():
    answer = client().get("/departments/dp-2/ancestors", headers=headers(MANAGER))
    assert answer.json()["data"][0]["id"] == "dp-1"


def test_the_route_opens_a_department_and_answers_201():
    answer = client().post("/departments", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "FIN", "name": "Finance"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_code_already_used():
    answer = client().post("/departments", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "OPS", "name": "Again"})
    assert answer.status_code == 409


def test_the_route_moves_a_department():
    answer = client().post("/departments/dp-3/move", headers=headers(MANAGER),
                           json={"parent_id": "dp-1"})
    assert answer.json()["parent_id"] == "dp-1"
