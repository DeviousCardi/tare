"""Reasons one person is not charged what everybody else is."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_contracts, seed_employees,
    seed_employers, seed_exemptions,
)
from tare.common.types import Exemption
from tare.modules.exemptions.rules import covers, kinds_standing, sort_by_start, standing_for
from tare.modules.exemptions.schemas import EndExemption, GrantExemption, ListExemptions
from tare.modules.exemptions.service import ExemptionsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_contracts(store)
    seed_exemptions(store)
    return store


def service():
    return ExemptionsService(a_store())


def an_exemption(**kw) -> Exemption:
    base = dict(id="ex-9", employee_id="ee-1", kind="contributions",
                reason="Over pension age", starts_on="2025-01-01", ends_on=None)
    return Exemption(**{**base, **kw})


def test_exemptions_read_earliest_first():
    rows = sort_by_start([an_exemption(starts_on="2025-06-01"), an_exemption(starts_on="2025-01-01")])
    assert [row.starts_on for row in rows] == ["2025-01-01", "2025-06-01"]


def test_an_exemption_covers_the_day_it_starts():
    assert covers(an_exemption(starts_on="2025-01-01"), "2025-01-01") is True


def test_an_exemption_does_not_cover_the_day_before_it_starts():
    assert covers(an_exemption(starts_on="2025-01-01"), "2024-12-31") is False


def test_an_exemption_still_covers_the_day_it_ends():
    assert covers(an_exemption(starts_on="2025-01-01", ends_on="2025-06-30"), "2025-06-30") is True


def test_an_exemption_does_not_cover_the_day_after_it_ends():
    assert covers(an_exemption(starts_on="2025-01-01", ends_on="2025-06-30"), "2025-07-01") is False


def test_an_open_exemption_covers_a_day_years_later():
    assert covers(an_exemption(starts_on="2025-01-01"), "2030-01-01") is True


def test_the_exemption_standing_for_somebody_is_found():
    found = standing_for(a_store().exemptions.all(), "ee-1", "contributions", "2025-06-01")
    assert found.id == "ex-1"


def test_an_exemption_that_has_ended_is_no_longer_standing():
    assert standing_for(a_store().exemptions.all(), "ee-2", "loan", "2025-09-01") is None


def test_an_exemption_of_another_kind_is_not_standing():
    assert standing_for(a_store().exemptions.all(), "ee-1", "levy", "2025-06-01") is None


def test_another_persons_exemption_is_not_standing_for_this_one():
    assert standing_for(a_store().exemptions.all(), "ee-2", "contributions", "2025-06-01") is None


def test_every_kind_somebody_is_exempt_from_is_reported():
    assert kinds_standing(a_store().exemptions.all(), "ee-1", "2025-06-01") == ["contributions"]


def test_somebody_exempt_from_nothing_reports_nothing():
    assert kinds_standing(a_store().exemptions.all(), "ee-3", "2025-06-01") == []


def test_an_exemption_that_had_not_started_reports_nothing():
    assert kinds_standing(a_store().exemptions.all(), "ee-1", "2024-06-01") == []


def test_the_bureau_lists_every_exemption():
    assert service().list(BUREAU, ListExemptions())["total"] == 3


def test_a_manager_lists_only_their_own_employers_exemptions():
    assert service().list(MANAGER, ListExemptions())["total"] == 2


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListExemptions(employee_id="ee-1"))["total"] == 1


def test_a_listing_can_be_narrowed_to_one_kind():
    assert service().list(BUREAU, ListExemptions(kind="levy"))["total"] == 1


def test_a_listing_can_be_narrowed_to_what_stood_on_a_day():
    assert service().list(BUREAU, ListExemptions(standing_on="2025-09-01"))["total"] == 2


def test_a_manager_cannot_narrow_a_listing_to_another_employers_person():
    with pytest.raises(Refused):
        service().list(MANAGER, ListExemptions(employee_id="ee-4"))


def test_an_exemption_can_be_read():
    assert service().get(MANAGER, "ex-1").reason == "Over pension age"


def test_an_exemption_nobody_granted_is_missing():
    with pytest.raises(NotFound, match="exemption ex-9 was not found"):
        service().get(BUREAU, "ex-9")


def test_a_manager_cannot_read_another_employers_exemption():
    with pytest.raises(Refused):
        service().get(MANAGER, "ex-3")


def test_an_exemption_is_granted():
    row = service().grant(MANAGER, GrantExemption(
        employee_id="ee-2", kind="levy", reason="Seconded", starts_on="2025-09-01"))
    assert row.kind == "levy" and row.ends_on is None


def test_an_exemption_can_be_granted_with_an_end_already_known():
    row = service().grant(MANAGER, GrantExemption(
        employee_id="ee-2", kind="levy", reason="Seconded",
        starts_on="2025-09-01", ends_on="2025-12-31"))
    assert row.ends_on == "2025-12-31"


def test_something_nobody_can_be_exempt_from_is_refused():
    with pytest.raises(Refused, match="is not something anybody can be exempt from"):
        service().grant(MANAGER, GrantExemption(
            employee_id="ee-2", kind="tax on air", reason="x", starts_on="2025-09-01"))


def test_an_exemption_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().grant(MANAGER, GrantExemption(
            employee_id="ee-2", kind="levy", reason="x",
            starts_on="2025-09-01", ends_on="2025-01-01"))


def test_a_second_exemption_of_one_kind_over_one_already_standing_is_refused():
    with pytest.raises(Conflict, match="already exempt from contributions"):
        service().grant(MANAGER, GrantExemption(
            employee_id="ee-1", kind="contributions", reason="Again",
            starts_on="2025-09-01"))


def test_a_manager_cannot_grant_an_exemption_at_another_employer():
    with pytest.raises(Refused):
        service().grant(MANAGER, GrantExemption(
            employee_id="ee-4", kind="loan", reason="x", starts_on="2025-09-01"))


def test_an_exemption_is_ended():
    assert service().end(MANAGER, "ex-1", EndExemption(ends_on="2025-09-30")).ends_on == "2025-09-30"


def test_an_exemption_cannot_end_twice():
    with pytest.raises(Conflict, match="already ended"):
        service().end(MANAGER, "ex-2", EndExemption(ends_on="2025-09-30"))


def test_an_exemption_cannot_be_ended_before_it_started():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().end(MANAGER, "ex-1", EndExemption(ends_on="2024-01-01"))


def test_ending_an_exemption_stops_it_standing_the_day_after():
    svc = service()
    svc.end(MANAGER, "ex-1", EndExemption(ends_on="2025-09-30"))
    assert svc.standing(MANAGER, "ee-1", "2025-10-01") == []


def test_what_somebody_is_exempt_from_is_reported():
    assert service().standing(MANAGER, "ee-1", "2025-06-01") == ["contributions"]


def client():
    return build_client(a_store())


def test_the_route_lists_exemptions():
    assert client().get("/exemptions", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_what_somebody_is_exempt_from():
    answer = client().get("/exemptions/standing/ee-1?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["kinds"] == ["contributions"]


def test_the_route_reads_one_exemption():
    assert client().get("/exemptions/ex-1", headers=headers(MANAGER)).json()["kind"] == "contributions"


def test_the_route_answers_404_for_an_exemption_nobody_granted():
    assert client().get("/exemptions/ex-9", headers=headers(BUREAU)).status_code == 404


def test_the_route_grants_an_exemption_and_answers_201():
    answer = client().post("/exemptions", headers=headers(MANAGER), json={
        "employee_id": "ee-2", "kind": "levy", "reason": "Seconded",
        "starts_on": "2025-09-01"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_an_exemption_already_standing():
    answer = client().post("/exemptions", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "kind": "contributions", "reason": "Again",
        "starts_on": "2025-09-01"})
    assert answer.status_code == 409


def test_the_route_ends_an_exemption():
    answer = client().post("/exemptions/ex-1/end", headers=headers(MANAGER),
                           json={"ends_on": "2025-09-30"})
    assert answer.json()["ends_on"] == "2025-09-30"
