"""Entitlements: how much leave somebody has, and how much is left of it."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_entitlements, seed_holidays, seed_leave,
)
from tare.common.types import Entitlement
from tare.modules.entitlements.rules import (
    MOST_CARRIED, carry_forward, earned_by, for_year, part_year, remaining,
    sort_by_year, total_available, year_ends_on,
)
from tare.modules.entitlements.schemas import (
    ChangeEntitlement, GrantEntitlement, ListEntitlements,
)
from tare.modules.entitlements.service import EntitlementsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_holidays(store)
    seed_leave(store)
    seed_entitlements(store)
    return store


def service():
    return EntitlementsService(a_store())


def an_entitlement(**kw) -> Entitlement:
    base = dict(id="en-9", employee_id="ee-1", employer_id="em-1",
                year_starts_on="2025-01-01", days=25, carried_in=3)
    return Entitlement(**{**base, **kw})


def test_entitlements_read_earliest_year_first():
    rows = sort_by_year([an_entitlement(year_starts_on="2025-01-01"),
                         an_entitlement(year_starts_on="2024-01-01")])
    assert [row.year_starts_on for row in rows] == ["2024-01-01", "2025-01-01"]


def test_a_leave_year_runs_a_year_less_a_day():
    assert year_ends_on(an_entitlement(year_starts_on="2025-01-01")) == "2025-12-31"


def test_a_leave_year_starting_mid_month_ends_a_year_less_a_day_later():
    assert year_ends_on(an_entitlement(year_starts_on="2025-04-06")) == "2026-04-05"


def test_the_entitlement_covering_a_day_is_found():
    assert for_year(a_store().entitlements.all(), "ee-1", "2025-06-01").id == "en-1"


def test_the_year_before_is_found_for_a_day_inside_it():
    assert for_year(a_store().entitlements.all(), "ee-1", "2024-06-01").id == "en-2"


def test_no_entitlement_covers_a_day_outside_every_year():
    assert for_year(a_store().entitlements.all(), "ee-1", "2030-01-01") is None


# Both seeded people were employed across the whole of the leave year, so what
# they earn does not depend on how a part year is treated.
def test_somebody_employed_all_year_earns_the_whole_entitlement():
    assert earned_by(an_entitlement(days=25), "2020-04-06", None) == 25


def test_an_entitlement_of_nothing_earns_nothing():
    assert earned_by(an_entitlement(days=0), "2020-04-06", None) == 0


def test_what_is_available_takes_in_what_was_carried_over():
    assert total_available(an_entitlement(days=25, carried_in=3), "2020-04-06", None) == 28


def test_nothing_carried_over_leaves_just_the_years_own_days():
    assert total_available(an_entitlement(days=25, carried_in=0), "2020-04-06", None) == 25


def test_what_is_left_is_what_is_available_less_what_was_taken():
    assert remaining(an_entitlement(days=25, carried_in=3), "2020-04-06", None, 10) == 18


def test_taking_everything_leaves_nothing():
    assert remaining(an_entitlement(days=25, carried_in=3), "2020-04-06", None, 28) == 0


def test_taking_more_than_was_available_still_leaves_nothing_rather_than_less():
    assert remaining(an_entitlement(days=25, carried_in=3), "2020-04-06", None, 40) == 0


def test_what_carries_forward_is_capped_at_what_the_rules_allow():
    assert (
        carry_forward(an_entitlement(days=25, carried_in=3), "2020-04-06", None, 0)
        == MOST_CARRIED
    )


def test_less_than_the_cap_carries_forward_whole():
    assert carry_forward(an_entitlement(days=25, carried_in=3), "2020-04-06", None, 26) == 2


def test_nothing_left_carries_nothing_forward():
    assert carry_forward(an_entitlement(days=25, carried_in=3), "2020-04-06", None, 28) == 0


def test_a_share_of_a_year_is_worth_a_share_of_the_days():
    # Half a 365-day year of 24 days is 12.
    assert part_year(an_entitlement(days=24, year_starts_on="2025-01-01"),
                     "2025-01-01", "2025-06-30") == 12


def test_a_whole_year_is_worth_the_whole_entitlement():
    assert part_year(an_entitlement(days=25, year_starts_on="2025-01-01"),
                     "2025-01-01", "2025-12-31") == 25


def test_the_bureau_lists_every_entitlement():
    assert service().list(BUREAU, ListEntitlements())["total"] == 3


def test_a_manager_lists_only_their_own_employers_entitlements():
    assert service().list(MANAGER, ListEntitlements())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_leave_year():
    assert service().list(MANAGER, ListEntitlements(year_starts_on="2025-01-01"))["total"] == 1


def test_an_entitlement_can_be_read():
    assert service().get(MANAGER, "en-1").days == 25


def test_an_entitlement_nobody_granted_is_missing():
    with pytest.raises(NotFound, match="entitlement en-9 was not found"):
        service().get(BUREAU, "en-9")


def test_a_manager_cannot_read_another_employers_entitlement():
    with pytest.raises(Refused):
        service().get(MANAGER, "en-3")


def test_an_entitlement_is_granted():
    row = service().grant(MANAGER, GrantEntitlement(
        employee_id="ee-2", year_starts_on="2025-01-01", days=20))
    assert row.days == 20 and row.carried_in == 0


def test_a_second_year_from_the_same_day_is_refused():
    with pytest.raises(Conflict, match="already has a year from"):
        service().grant(MANAGER, GrantEntitlement(
            employee_id="ee-1", year_starts_on="2025-01-01", days=25))


def test_an_entitlement_is_changed():
    assert service().change(MANAGER, "en-1", ChangeEntitlement(days=27)).days == 27


def test_changing_nothing_is_refused():
    with pytest.raises(Refused, match="nothing was asked to change"):
        service().change(MANAGER, "en-1", ChangeEntitlement())


def test_the_balance_reports_what_is_available_and_what_is_left():
    answer = service().balance(MANAGER, "ee-1", "2025-06-01")
    assert answer["available"] == 28 and answer["taken"] == 10 and answer["remaining"] == 18


def test_the_balance_names_the_leave_year_it_is_for():
    answer = service().balance(MANAGER, "ee-1", "2025-06-01")
    assert answer["year_starts_on"] == "2025-01-01" and answer["year_ends_on"] == "2025-12-31"


def test_a_day_no_entitlement_covers_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="entitlement covering"):
        service().balance(MANAGER, "ee-1", "2030-01-01")


def client():
    return build_client(a_store())


def test_the_route_lists_entitlements():
    assert client().get("/entitlements", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_a_balance():
    answer = client().get("/entitlements/balance/ee-1?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["remaining"] == 18


def test_the_route_grants_an_entitlement_and_answers_201():
    answer = client().post("/entitlements", headers=headers(MANAGER), json={
        "employee_id": "ee-2", "year_starts_on": "2025-01-01", "days": 20})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_second_year_from_one_day():
    answer = client().post("/entitlements", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "year_starts_on": "2025-01-01", "days": 25})
    assert answer.status_code == 409


def test_the_route_changes_an_entitlement():
    answer = client().post("/entitlements/en-1/change", headers=headers(MANAGER),
                           json={"days": 27})
    assert answer.json()["days"] == 27
