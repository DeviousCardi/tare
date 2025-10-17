"""Employers: who is on the books, who may see them, and who may change them."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import BUREAU, CLERK, MANAGER, build_client, build_store, headers, seed_employers
from tare.modules.employers.rules import is_open_on, next_reference, pay_day_of, sort_by_reference
from tare.modules.employers.schemas import CloseEmployer, ListEmployers, TakeOnEmployer
from tare.modules.employers.service import EmployersService
from tare.common.types import Employer


def service():
    store = build_store()
    seed_employers(store)
    return EmployersService(store)


def an_employer(**kw) -> Employer:
    base = dict(id="em-9", reference="E-0009", name="Test", opened_on="2024-01-01",
                closed_on=None, pay_day=28)
    return Employer(**{**base, **kw})


def test_employers_read_in_reference_order():
    rows = sort_by_reference([an_employer(reference="E-0002"), an_employer(reference="E-0001")])
    assert [row.reference for row in rows] == ["E-0001", "E-0002"]


def test_the_first_employer_taken_on_is_numbered_one():
    assert next_reference([]) == "E-0001"


def test_the_next_reference_follows_the_highest_already_issued():
    assert next_reference([an_employer(reference="E-0001"), an_employer(reference="E-0004")]) == "E-0005"


def test_a_closed_employer_does_not_free_its_reference_for_reuse():
    rows = [an_employer(reference="E-0001"), an_employer(reference="E-0002", closed_on="2024-06-01")]
    assert next_reference(rows) == "E-0003"


def test_an_employer_is_open_on_the_day_they_were_taken_on():
    assert is_open_on(an_employer(opened_on="2024-01-01"), "2024-01-01") is True


def test_an_employer_is_not_open_the_day_before_they_were_taken_on():
    assert is_open_on(an_employer(opened_on="2024-01-01"), "2023-12-31") is False


def test_an_employer_is_still_open_on_the_day_they_closed():
    row = an_employer(opened_on="2024-01-01", closed_on="2024-06-30")
    assert is_open_on(row, "2024-06-30") is True


def test_an_employer_is_not_open_the_day_after_they_closed():
    row = an_employer(opened_on="2024-01-01", closed_on="2024-06-30")
    assert is_open_on(row, "2024-07-01") is False


def test_an_employer_that_never_closed_is_open_years_later():
    assert is_open_on(an_employer(opened_on="2024-01-01"), "2030-01-01") is True


def test_a_pay_day_lands_on_that_day_of_the_month():
    assert pay_day_of(an_employer(pay_day=28), "2025-04-01") == "2025-04-28"


def test_a_pay_day_past_the_end_of_a_short_month_falls_on_its_last_day():
    assert pay_day_of(an_employer(pay_day=31), "2025-04-01") == "2025-04-30"


def test_a_pay_day_past_the_end_of_february_falls_on_its_last_day():
    assert pay_day_of(an_employer(pay_day=30), "2025-02-01") == "2025-02-28"


def test_a_pay_day_in_a_leap_february_reaches_the_twenty_ninth():
    assert pay_day_of(an_employer(pay_day=30), "2024-02-01") == "2024-02-29"


def test_the_bureau_lists_every_employer():
    assert service().list(BUREAU, ListEmployers()).get("total") == 2


def test_a_manager_lists_only_their_own_employer():
    answer = service().list(MANAGER, ListEmployers())
    assert answer["total"] == 1 and answer["data"][0].id == "em-1"


def test_a_clerk_lists_only_their_own_employer():
    assert service().list(CLERK, ListEmployers())["total"] == 1


def test_a_listing_can_be_narrowed_to_who_was_open_on_a_day():
    assert service().list(BUREAU, ListEmployers(open_on="2024-02-01"))["total"] == 1


def test_a_listing_narrowed_on_a_day_that_is_not_a_date_is_refused():
    with pytest.raises(Refused, match="not a calendar date"):
        service().list(BUREAU, ListEmployers(open_on="2024-02-30"))


def test_an_employer_can_be_read_by_the_bureau():
    assert service().get(BUREAU, "em-2").name == "Verrin Freight"


def test_a_manager_cannot_read_another_employer():
    with pytest.raises(Refused, match="cannot see employer em-2"):
        service().get(MANAGER, "em-2")


def test_an_employer_nobody_has_on_the_books_is_missing():
    with pytest.raises(NotFound, match="employer em-9 was not found"):
        service().get(BUREAU, "em-9")


def test_the_visibility_check_passes_for_an_operators_own_employer():
    assert service().assert_visible(MANAGER, "em-1") is None


def test_the_visibility_check_refuses_another_employer():
    with pytest.raises(Refused):
        service().assert_visible(CLERK, "em-2")


def test_the_visibility_check_calls_an_unknown_employer_missing_rather_than_hidden():
    with pytest.raises(NotFound):
        service().assert_visible(BUREAU, "em-404")


def test_the_bureau_takes_an_employer_onto_the_books():
    row = service().take_on(BUREAU, TakeOnEmployer(
        name="Ashgrove Mills", opened_on="2025-01-06", pay_day=25))
    assert row.name == "Ashgrove Mills" and row.closed_on is None


def test_an_employer_taken_on_is_numbered_after_the_ones_already_there():
    assert service().take_on(BUREAU, TakeOnEmployer(
        name="Ashgrove Mills", opened_on="2025-01-06", pay_day=25)).reference == "E-0003"


def test_nobody_but_the_bureau_may_take_on_an_employer():
    with pytest.raises(Refused, match="only the bureau may take on an employer"):
        service().take_on(MANAGER, TakeOnEmployer(
            name="Ashgrove Mills", opened_on="2025-01-06", pay_day=25))


def test_taking_on_an_employer_on_a_day_that_is_not_a_date_is_refused():
    with pytest.raises(Refused, match="not a calendar date"):
        service().take_on(BUREAU, TakeOnEmployer(
            name="Ashgrove Mills", opened_on="2025-02-30", pay_day=25))


def test_a_reference_already_on_the_books_is_refused():
    with pytest.raises(Conflict, match="already on the books"):
        service().take_on(BUREAU, TakeOnEmployer(
            name="Ashgrove Mills", opened_on="2025-01-06", pay_day=25, reference="E-0001"))


def test_the_bureau_closes_an_employer():
    assert service().close(BUREAU, "em-1", CloseEmployer(closed_on="2025-06-30")).closed_on == "2025-06-30"


def test_an_employer_cannot_be_closed_twice():
    svc = service()
    svc.close(BUREAU, "em-1", CloseEmployer(closed_on="2025-06-30"))
    with pytest.raises(Conflict, match="already closed"):
        svc.close(BUREAU, "em-1", CloseEmployer(closed_on="2025-07-31"))


def test_an_employer_cannot_close_before_they_were_taken_on():
    with pytest.raises(Refused, match="cannot close before it was taken on"):
        service().close(BUREAU, "em-1", CloseEmployer(closed_on="2023-01-01"))


def test_nobody_but_the_bureau_may_close_an_employer():
    with pytest.raises(Refused, match="only the bureau may close an employer"):
        service().close(MANAGER, "em-1", CloseEmployer(closed_on="2025-06-30"))


def client_and_store():
    store = build_store()
    seed_employers(store)
    return build_client(store)


def test_the_route_lists_employers_for_the_bureau():
    answer = client_and_store().get("/employers", headers=headers(BUREAU)).json()
    assert answer["total"] == 2


def test_the_route_narrows_the_listing_to_a_managers_own_employer():
    answer = client_and_store().get("/employers", headers=headers(MANAGER)).json()
    assert [row["id"] for row in answer["data"]] == ["em-1"]


def test_the_route_refuses_a_request_with_no_operator_on_it():
    assert client_and_store().get("/employers").status_code == 400


def test_the_route_reads_one_employer():
    answer = client_and_store().get("/employers/em-1", headers=headers(BUREAU)).json()
    assert answer["reference"] == "E-0001"


def test_the_route_answers_404_for_an_employer_nobody_has():
    assert client_and_store().get("/employers/em-9", headers=headers(BUREAU)).status_code == 404


def test_the_route_answers_400_when_a_manager_reaches_for_another_employer():
    assert client_and_store().get("/employers/em-2", headers=headers(MANAGER)).status_code == 400


def test_the_route_takes_an_employer_on_and_answers_201():
    answer = client_and_store().post("/employers", headers=headers(BUREAU), json={
        "name": "Ashgrove Mills", "opened_on": "2025-01-06", "pay_day": 25})
    assert answer.status_code == 201 and answer.json()["reference"] == "E-0003"


def test_the_route_answers_409_for_a_reference_already_on_the_books():
    answer = client_and_store().post("/employers", headers=headers(BUREAU), json={
        "name": "X", "opened_on": "2025-01-06", "pay_day": 25, "reference": "E-0001"})
    assert answer.status_code == 409


def test_the_route_closes_an_employer():
    answer = client_and_store().post("/employers/em-1/close", headers=headers(BUREAU),
                                     json={"closed_on": "2025-06-30"})
    assert answer.json()["closed_on"] == "2025-06-30"


def test_the_route_refuses_a_pay_day_outside_the_month():
    answer = client_and_store().post("/employers", headers=headers(BUREAU), json={
        "name": "X", "opened_on": "2025-01-06", "pay_day": 40})
    assert answer.status_code == 422
