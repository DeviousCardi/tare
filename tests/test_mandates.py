"""Mandates: where somebody's pay is sent."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_mandates,
)
from tare.common.types import Mandate
from tare.modules.mandates.rules import holders_of, sort_by_start, standing_for, stands_on
from tare.modules.mandates.schemas import EndMandate, ListMandates, SetMandate
from tare.modules.mandates.service import MandatesService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_mandates):
        seed(store)
    return store


def service():
    return MandatesService(a_store())


def a_mandate(**kw) -> Mandate:
    base = dict(id="md-9", employee_id="ee-1", employer_id="em-1",
                account="20-11-45/40028761", holder="N Harrow",
                starts_on="2024-01-01", ends_on=None)
    return Mandate(**{**base, **kw})


def test_mandates_read_earliest_first():
    rows = sort_by_start([a_mandate(starts_on="2025-06-01"), a_mandate(starts_on="2024-01-01")])
    assert [row.starts_on for row in rows] == ["2024-01-01", "2025-06-01"]


def test_a_mandate_stands_on_the_day_it_starts():
    assert stands_on(a_mandate(starts_on="2024-01-01"), "2024-01-01") is True


def test_a_mandate_does_not_stand_the_day_before_it_starts():
    assert stands_on(a_mandate(starts_on="2024-01-01"), "2023-12-31") is False


def test_a_mandate_still_stands_on_the_day_it_ends():
    assert stands_on(a_mandate(ends_on="2025-05-31"), "2025-05-31") is True


def test_a_mandate_does_not_stand_the_day_after_it_ends():
    assert stands_on(a_mandate(ends_on="2025-05-31"), "2025-06-01") is False


def test_the_mandate_somebody_is_paid_into_is_found():
    assert standing_for(a_store().mandates.all(), "ee-1", "2025-08-01").id == "md-2"


def test_the_older_mandate_stands_before_the_change():
    assert standing_for(a_store().mandates.all(), "ee-1", "2025-01-01").id == "md-1"


def test_nobody_is_on_a_mandate_before_it_starts():
    assert standing_for(a_store().mandates.all(), "ee-2", "2025-01-01") is None


def test_the_names_a_run_of_mandates_is_held_in_are_reported():
    mine = [row for row in a_store().mandates.all() if row.employee_id == "ee-1"]
    assert holders_of(mine) == ["N Harrow"]


def test_no_mandates_are_held_in_no_names():
    assert holders_of([]) == []


def test_the_bureau_lists_every_mandate():
    assert service().list(BUREAU, ListMandates())["total"] == 4


def test_a_manager_lists_only_their_own_employers_mandates():
    assert service().list(MANAGER, ListMandates())["total"] == 3


def test_a_listing_can_be_narrowed_to_a_day():
    assert service().list(MANAGER, ListMandates(standing_on="2025-08-01"))["total"] == 2


def test_a_mandate_can_be_read():
    assert service().get(MANAGER, "md-1").holder == "N Harrow"


def test_a_mandate_nobody_set_is_missing():
    with pytest.raises(NotFound, match="mandate md-9 was not found"):
        service().get(BUREAU, "md-9")


def test_a_manager_cannot_read_another_employers_mandate():
    with pytest.raises(Refused):
        service().get(MANAGER, "md-4")


def test_a_mandate_is_set():
    row = service().set(MANAGER, SetMandate(
        employee_id="ee-3", account="11-22-33/12345678", holder="J Fenn",
        starts_on="2025-01-01"))
    assert row.ends_on is None


def test_setting_a_mandate_ends_the_one_before_it_the_day_before():
    svc = service()
    svc.set(MANAGER, SetMandate(
        employee_id="ee-1", account="11-22-33/12345678", holder="N Harrow",
        starts_on="2025-09-01"))
    assert svc.get(MANAGER, "md-2").ends_on == "2025-08-31"


def test_a_second_mandate_starting_the_same_day_is_refused():
    with pytest.raises(Conflict, match="already starts on"):
        service().set(MANAGER, SetMandate(
            employee_id="ee-1", account="11-22-33/12345678", holder="N Harrow",
            starts_on="2025-06-01"))


def test_an_account_that_does_not_read_as_one_is_refused():
    with pytest.raises(Refused, match="does not read as an account"):
        service().set(MANAGER, SetMandate(
            employee_id="ee-3", account="nonsense", holder="J Fenn",
            starts_on="2025-01-01"))


def test_a_mandate_is_ended():
    assert service().end(MANAGER, "md-2", EndMandate(ends_on="2025-09-30")).ends_on == "2025-09-30"


def test_a_mandate_cannot_end_twice():
    with pytest.raises(Conflict, match="already ended"):
        service().end(MANAGER, "md-1", EndMandate(ends_on="2025-09-30"))


def test_a_mandate_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().end(MANAGER, "md-2", EndMandate(ends_on="2024-01-01"))


def test_the_mandate_standing_for_somebody_is_reported():
    assert service().standing(MANAGER, "ee-1", "2025-08-01").account == "20-11-45/40028762"


def test_a_day_no_mandate_covers_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="mandate standing"):
        service().standing(MANAGER, "ee-2", "2025-01-01")


def client():
    return build_client(a_store())


def test_the_route_lists_mandates():
    assert client().get("/mandates", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reports_the_mandate_standing():
    answer = client().get("/mandates/standing/ee-1?on=2025-08-01", headers=headers(MANAGER))
    assert answer.json()["id"] == "md-2"


def test_the_route_sets_a_mandate_and_answers_201():
    answer = client().post("/mandates", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "account": "11-22-33/12345678", "holder": "J Fenn",
        "starts_on": "2025-01-01"})
    assert answer.status_code == 201


def test_the_route_ends_a_mandate():
    answer = client().post("/mandates/md-2/end", headers=headers(MANAGER),
                           json={"ends_on": "2025-09-30"})
    assert answer.json()["ends_on"] == "2025-09-30"
