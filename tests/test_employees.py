"""The people an employer pays: who they are, and who may look at them."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, CLERK, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
)
from tare.common.types import Employee
from tare.modules.employees.rules import (
    age_on, days_in_post, in_post_on, next_reference, sort_by_name, sort_by_reference,
)
from tare.modules.employees.schemas import (
    ChangeLevyCode, LeaveEmployee, ListEmployees, TakeOnEmployee,
)
from tare.modules.employees.service import EmployeesService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    return store


def service():
    return EmployeesService(a_store())


def a_person(**kw) -> Employee:
    base = dict(id="ee-9", employer_id="em-1", reference="em-1/0009", name="Ada Quill",
                joined_on="2024-01-01", left_on=None, date_of_birth="1990-01-01",
                levy_code="L1")
    return Employee(**{**base, **kw})


def test_people_read_in_reference_order():
    rows = sort_by_reference([a_person(reference="b"), a_person(reference="a")])
    assert [row.reference for row in rows] == ["a", "b"]


def test_a_register_reads_by_surname():
    rows = sort_by_name([a_person(name="Ada Quill"), a_person(name="Zed Abbott")])
    assert [row.name for row in rows] == ["Zed Abbott", "Ada Quill"]


def test_two_people_sharing_a_surname_fall_back_to_their_reference():
    rows = sort_by_name([a_person(name="B Quill", reference="b"),
                         a_person(name="A Quill", reference="a")])
    assert [row.reference for row in rows] == ["a", "b"]


def test_the_first_person_at_an_employer_is_numbered_one():
    assert next_reference([], "em-1") == "em-1/0001"


def test_references_run_per_employer_so_both_have_a_first():
    rows = [a_person(employer_id="em-1", reference="em-1/0001")]
    assert next_reference(rows, "em-2") == "em-2/0001"


def test_the_next_reference_follows_the_highest_at_that_employer():
    rows = [a_person(reference="em-1/0001"), a_person(reference="em-1/0007")]
    assert next_reference(rows, "em-1") == "em-1/0008"


def test_somebody_is_in_post_on_the_day_they_joined():
    assert in_post_on(a_person(joined_on="2024-01-01"), "2024-01-01") is True


def test_nobody_is_in_post_the_day_before_they_joined():
    assert in_post_on(a_person(joined_on="2024-01-01"), "2023-12-31") is False


def test_somebody_is_still_in_post_on_the_day_they_left():
    assert in_post_on(a_person(joined_on="2024-01-01", left_on="2024-06-30"), "2024-06-30") is True


def test_nobody_is_in_post_the_day_after_they_left():
    assert in_post_on(a_person(joined_on="2024-01-01", left_on="2024-06-30"), "2024-07-01") is False


def test_an_age_counts_whole_years():
    assert age_on(a_person(date_of_birth="1990-06-15"), "2025-06-15") == 35


def test_an_age_turns_over_on_the_birthday_itself():
    assert age_on(a_person(date_of_birth="1990-06-15"), "2025-06-14") == 34


def test_an_age_before_the_birthday_in_the_year_is_a_year_less():
    assert age_on(a_person(date_of_birth="1990-12-31"), "2025-01-01") == 34


def test_days_in_post_count_both_ends():
    assert days_in_post(a_person(joined_on="2025-04-01"), "2025-04-30") == 30


def test_days_in_post_stop_on_the_day_somebody_left():
    row = a_person(joined_on="2025-04-01", left_on="2025-04-10")
    assert days_in_post(row, "2025-04-30") == 10


def test_days_in_post_are_none_before_somebody_joined():
    assert days_in_post(a_person(joined_on="2025-04-01"), "2025-03-01") == 0


def test_the_bureau_lists_everybody():
    assert service().list(BUREAU, ListEmployees())["total"] == 4


def test_a_manager_lists_only_their_own_employers_people():
    assert service().list(MANAGER, ListEmployees())["total"] == 3


def test_a_listing_can_be_narrowed_to_one_employer():
    assert service().list(BUREAU, ListEmployees(employer_id="em-2"))["total"] == 1


def test_a_manager_cannot_narrow_a_listing_to_another_employer():
    with pytest.raises(Refused, match="cannot see employer em-2"):
        service().list(MANAGER, ListEmployees(employer_id="em-2"))


def test_a_listing_can_be_narrowed_to_who_was_in_post_on_a_day():
    # Bram joined in July 2025 and Joss left that May, so only two of em-1's
    # three were in post in June, plus em-2's one.
    assert service().list(BUREAU, ListEmployees(in_post_on="2025-06-15"))["total"] == 2


def test_a_listing_can_be_read_by_surname():
    rows = service().list(BUREAU, ListEmployees(by_name=True))["data"]
    assert rows[0].name == "Wren Attley"


def test_a_person_can_be_read():
    assert service().get(BUREAU, "ee-1").name == "Nell Harrow"


def test_a_manager_cannot_read_somebody_at_another_employer():
    with pytest.raises(Refused):
        service().get(MANAGER, "ee-4")


def test_a_person_nobody_has_is_missing():
    with pytest.raises(NotFound, match="employee ee-9 was not found"):
        service().get(BUREAU, "ee-9")


def test_a_person_is_taken_onto_the_payroll():
    row = service().take_on(MANAGER, TakeOnEmployee(
        employer_id="em-1", name="Ada Quill", joined_on="2025-09-01",
        date_of_birth="1992-02-02", levy_code="L1"))
    assert row.reference == "em-1/0004" and row.left_on is None


def test_a_manager_cannot_take_somebody_onto_another_employers_payroll():
    with pytest.raises(Refused):
        service().take_on(MANAGER, TakeOnEmployee(
            employer_id="em-2", name="Ada Quill", joined_on="2025-09-01",
            date_of_birth="1992-02-02", levy_code="L1"))


def test_taking_somebody_on_with_a_birth_day_that_is_not_a_date_is_refused():
    with pytest.raises(Refused, match="not a calendar date"):
        service().take_on(MANAGER, TakeOnEmployee(
            employer_id="em-1", name="Ada Quill", joined_on="2025-09-01",
            date_of_birth="1992-02-30", levy_code="L1"))


def test_a_reference_already_on_the_payroll_is_refused():
    with pytest.raises(Conflict, match="already on the payroll"):
        service().take_on(MANAGER, TakeOnEmployee(
            employer_id="em-1", name="Ada Quill", joined_on="2025-09-01",
            date_of_birth="1992-02-02", levy_code="L1", reference="em-1/0001"))


def test_somebody_leaves_the_payroll():
    assert service().leave(MANAGER, "ee-1", LeaveEmployee(left_on="2025-09-30")).left_on == "2025-09-30"


def test_nobody_leaves_twice():
    with pytest.raises(Conflict, match="has already left"):
        service().leave(MANAGER, "ee-3", LeaveEmployee(left_on="2025-09-30"))


def test_nobody_leaves_before_they_joined():
    with pytest.raises(Refused, match="leave before they joined"):
        service().leave(MANAGER, "ee-1", LeaveEmployee(left_on="2019-01-01"))


def test_a_levy_code_can_be_changed():
    assert service().change_levy_code(MANAGER, "ee-1", ChangeLevyCode(levy_code="L3")).levy_code == "L3"


def test_a_manager_cannot_change_a_levy_code_at_another_employer():
    with pytest.raises(Refused):
        service().change_levy_code(MANAGER, "ee-4", ChangeLevyCode(levy_code="L3"))


def client():
    return build_client(a_store())


def test_the_route_lists_people():
    assert client().get("/employees", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_narrows_a_listing_to_a_clerks_own_employer():
    assert client().get("/employees", headers=headers(CLERK)).json()["total"] == 3


def test_the_route_reads_one_person():
    assert client().get("/employees/ee-1", headers=headers(BUREAU)).json()["name"] == "Nell Harrow"


def test_the_route_answers_404_for_somebody_nobody_has():
    assert client().get("/employees/ee-9", headers=headers(BUREAU)).status_code == 404


def test_the_route_takes_somebody_on_and_answers_201():
    answer = client().post("/employees", headers=headers(MANAGER), json={
        "employer_id": "em-1", "name": "Ada Quill", "joined_on": "2025-09-01",
        "date_of_birth": "1992-02-02", "levy_code": "L1"})
    assert answer.status_code == 201


def test_the_route_marks_somebody_as_left():
    answer = client().post("/employees/ee-1/leave", headers=headers(MANAGER),
                           json={"left_on": "2025-09-30"})
    assert answer.json()["left_on"] == "2025-09-30"


def test_the_route_answers_409_when_somebody_leaves_twice():
    answer = client().post("/employees/ee-3/leave", headers=headers(MANAGER),
                           json={"left_on": "2025-09-30"})
    assert answer.status_code == 409


def test_the_route_changes_a_levy_code():
    answer = client().post("/employees/ee-1/levy-code", headers=headers(MANAGER),
                           json={"levy_code": "L4"})
    assert answer.json()["levy_code"] == "L4"
