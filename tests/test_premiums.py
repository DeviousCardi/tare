"""Premiums: the uplift for working at a time somebody would rather not."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_premiums,
)
from tare.common.types import Premium
from tare.modules.premiums.rules import (
    applies_on, best_of, covers_hour, premium_on, sort_by_code,
)
from tare.modules.premiums.schemas import DefinePremium, ListPremiums
from tare.modules.premiums.service import PremiumsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_premiums(store)
    return store


def service():
    return PremiumsService(a_store())


def a_premium(**kw) -> Premium:
    base = dict(id="pm-9", employer_id="em-1", code="NIGHT", name="Night",
                rate_basis_points=3000, from_hour=22, to_hour=6, weekend_only=False)
    return Premium(**{**base, **kw})


def test_premiums_read_in_code_order():
    rows = sort_by_code([a_premium(code="WKND"), a_premium(code="NIGHT")])
    assert [row.code for row in rows] == ["NIGHT", "WKND"]


def test_a_window_inside_one_day_covers_its_own_hours():
    assert covers_hour(a_premium(from_hour=9, to_hour=17), 12) is True


def test_a_window_does_not_cover_the_hour_it_ends_on():
    assert covers_hour(a_premium(from_hour=9, to_hour=17), 17) is False


def test_a_window_covers_the_hour_it_starts_on():
    assert covers_hour(a_premium(from_hour=9, to_hour=17), 9) is True


def test_a_window_wrapping_past_midnight_covers_the_late_hours():
    assert covers_hour(a_premium(from_hour=22, to_hour=6), 23) is True


def test_a_window_wrapping_past_midnight_covers_the_early_hours():
    assert covers_hour(a_premium(from_hour=22, to_hour=6), 2) is True


def test_a_window_wrapping_past_midnight_leaves_the_middle_of_the_day_alone():
    assert covers_hour(a_premium(from_hour=22, to_hour=6), 12) is False


def test_an_everyday_premium_applies_on_a_weekday():
    assert applies_on(a_premium(weekend_only=False), "2025-06-04") is True


def test_a_weekend_premium_does_not_apply_on_a_weekday():
    assert applies_on(a_premium(weekend_only=True), "2025-06-04") is False


def test_a_weekend_premium_applies_on_a_saturday():
    assert applies_on(a_premium(weekend_only=True), "2025-06-07") is True


# Every hourly rate below divides evenly at the uplift rate, so no fraction of
# a penny is left over and the answer does not depend on where the rounding is
# done.
def test_an_uplift_is_its_share_of_the_hourly_rate_for_each_hour():
    assert premium_on(a_premium(rate_basis_points=3000), 1000, 8) == 2400


def test_an_uplift_over_one_hour_is_its_share_of_that_hour():
    assert premium_on(a_premium(rate_basis_points=5000), 1000, 1) == 500


def test_an_uplift_over_no_hours_comes_to_nothing():
    assert premium_on(a_premium(), 1000, 0) == 0


def test_an_uplift_on_no_pay_comes_to_nothing():
    assert premium_on(a_premium(), 0, 8) == 0


def test_a_premium_of_no_rate_upflifts_nothing():
    assert premium_on(a_premium(rate_basis_points=0), 1000, 8) == 0


def test_the_premium_worth_most_wins_where_two_cover_an_hour():
    rows = [a_premium(id="a", code="A", rate_basis_points=3000, from_hour=0, to_hour=23),
            a_premium(id="b", code="B", rate_basis_points=5000, from_hour=0, to_hour=23)]
    assert best_of(rows, 12, "2025-06-04").id == "b"


def test_no_premium_covers_an_hour_none_of_them_reaches():
    assert best_of([a_premium(from_hour=22, to_hour=6)], 12, "2025-06-04") is None


def test_a_weekend_premium_is_passed_over_on_a_weekday():
    rows = [a_premium(weekend_only=True, from_hour=0, to_hour=23)]
    assert best_of(rows, 12, "2025-06-04") is None


def test_the_bureau_lists_every_premium():
    assert service().list(BUREAU, ListPremiums())["total"] == 3


def test_a_manager_lists_only_their_own_employers_premiums():
    assert service().list(MANAGER, ListPremiums())["total"] == 2


def test_a_listing_can_be_narrowed_to_an_hour():
    # The weekend premium runs to 23 without covering it, so only the night
    # one reaches that hour.
    assert service().list(MANAGER, ListPremiums(covering_hour=23))["total"] == 1


def test_a_premium_can_be_read():
    assert service().get(MANAGER, "pm-1").rate_basis_points == 3000


def test_a_premium_nobody_defined_is_missing():
    with pytest.raises(NotFound, match="premium pm-9 was not found"):
        service().get(BUREAU, "pm-9")


def test_a_manager_cannot_read_another_employers_premium():
    with pytest.raises(Refused):
        service().get(MANAGER, "pm-3")


def test_a_premium_is_defined():
    row = service().define(MANAGER, DefinePremium(
        employer_id="em-1", code="EVE", name="Evening", rate_basis_points=2000,
        from_hour=18, to_hour=22))
    assert row.code == "EVE"


def test_a_premium_that_starts_and_ends_on_the_hour_is_refused():
    with pytest.raises(Refused, match="covers nothing"):
        service().define(MANAGER, DefinePremium(
            employer_id="em-1", code="EVE", name="Evening", rate_basis_points=2000,
            from_hour=18, to_hour=18))


def test_a_code_the_employer_already_uses_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().define(MANAGER, DefinePremium(
            employer_id="em-1", code="NIGHT", name="Again", rate_basis_points=1,
            from_hour=1, to_hour=2))


def test_the_best_premium_for_an_hour_is_reported():
    assert service().best_for(MANAGER, "em-1", 23, "2025-06-04").code == "NIGHT"


def test_no_premium_for_an_hour_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="premium covering"):
        service().best_for(MANAGER, "em-1", 12, "2025-06-04")


def test_what_an_uplift_comes_to_is_reported():
    assert service().uplift(MANAGER, "pm-1", 1000, 8)["uplift"] == 2400


def test_negative_hours_are_refused():
    with pytest.raises(Refused, match="cannot be negative"):
        service().uplift(MANAGER, "pm-1", 1000, -1)


def client():
    return build_client(a_store())


def test_the_route_lists_premiums():
    assert client().get("/premiums", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_the_best_premium_for_an_hour():
    answer = client().get("/premiums/best?employer_id=em-1&hour=23&on=2025-06-04",
                          headers=headers(MANAGER))
    assert answer.json()["code"] == "NIGHT"


def test_the_route_reports_an_uplift():
    answer = client().get("/premiums/pm-1/uplift?hourly_pay=1000&hours=8",
                          headers=headers(MANAGER))
    assert answer.json()["uplift"] == 2400


def test_the_route_defines_a_premium_and_answers_201():
    answer = client().post("/premiums", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "EVE", "name": "Evening",
        "rate_basis_points": 2000, "from_hour": 18, "to_hour": 22})
    assert answer.status_code == 201
