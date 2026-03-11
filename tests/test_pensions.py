"""Pension schemes, and what a figure of pensionable pay puts in."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_providers,
    seed_schemes,
)
from tare.common.types import PensionScheme
from tare.modules.pensions.rules import (
    employee_share, employer_share, is_open_on, qualifies, sort_by_code, total_share,
)
from tare.modules.pensions.schemas import CloseScheme, ListSchemes, OpenScheme
from tare.modules.pensions.service import PensionsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_providers, seed_schemes):
        seed(store)
    return store


def service():
    return PensionsService(a_store())


def a_scheme(**kw) -> PensionScheme:
    base = dict(id="sc-9", employer_id="em-1", provider_id="pv-1", code="MAIN",
                name="Main", employee_basis_points=500, employer_basis_points=300,
                qualifying_floor=120000, opened_on="2024-01-01", closed_on=None)
    return PensionScheme(**{**base, **kw})


def test_schemes_read_in_code_order():
    rows = sort_by_code([a_scheme(code="OLD"), a_scheme(code="MAIN")])
    assert [row.code for row in rows] == ["MAIN", "OLD"]


def test_a_scheme_is_open_on_the_day_it_opened():
    assert is_open_on(a_scheme(opened_on="2024-01-01"), "2024-01-01") is True


def test_a_scheme_is_not_open_the_day_before_it_opened():
    assert is_open_on(a_scheme(opened_on="2024-01-01"), "2023-12-31") is False


def test_a_scheme_is_still_open_on_the_day_it_closed():
    assert is_open_on(a_scheme(closed_on="2024-12-31"), "2024-12-31") is True


def test_a_scheme_is_not_open_the_day_after_it_closed():
    assert is_open_on(a_scheme(closed_on="2024-12-31"), "2025-01-01") is False


# Every figure below sits clearly above or clearly below the scheme's floor,
# never exactly on it, so who comes into the scheme does not depend on how a
# figure landing on the floor is read.
def test_pay_well_above_the_floor_brings_somebody_into_the_scheme():
    assert qualifies(a_scheme(qualifying_floor=120000), 200000) is True


def test_pay_well_below_the_floor_does_not():
    assert qualifies(a_scheme(qualifying_floor=120000), 80000) is False


def test_no_pay_at_all_does_not_bring_anybody_in():
    assert qualifies(a_scheme(qualifying_floor=120000), 0) is False


def test_a_scheme_with_no_floor_takes_anybody_who_earns_anything():
    assert qualifies(a_scheme(qualifying_floor=0), 1) is True


def test_the_member_puts_in_their_own_share():
    assert employee_share(a_scheme(employee_basis_points=500), 200000) == 10000


def test_the_employer_puts_in_theirs_on_top():
    assert employer_share(a_scheme(employer_basis_points=300), 200000) == 6000


def test_the_two_shares_come_to_the_whole():
    assert total_share(a_scheme(), 200000) == 16000


def test_no_pensionable_pay_puts_in_nothing():
    assert total_share(a_scheme(), 0) == 0


def test_a_share_rounds_half_up():
    # 100050 at 5% is 5002.5, which rounds to 5003.
    assert employee_share(a_scheme(employee_basis_points=500), 100050) == 5003


def test_the_bureau_lists_every_scheme():
    assert service().list(BUREAU, ListSchemes())["total"] == 3


def test_a_manager_lists_only_their_own_employers_schemes():
    assert service().list(MANAGER, ListSchemes())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_was_open_on_a_day():
    assert service().list(MANAGER, ListSchemes(open_on="2025-06-01"))["total"] == 1


def test_a_scheme_can_be_read():
    assert service().get(MANAGER, "sc-1").name == "Halloway main"


def test_a_scheme_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="scheme sc-9 was not found"):
        service().get(BUREAU, "sc-9")


def test_a_manager_cannot_read_another_employers_scheme():
    with pytest.raises(Refused):
        service().get(MANAGER, "sc-3")


def test_a_scheme_is_opened():
    row = service().open(MANAGER, OpenScheme(
        employer_id="em-1", provider_id="pv-1", code="NEW", name="New",
        employee_basis_points=600, employer_basis_points=400,
        qualifying_floor=130000, opened_on="2025-04-06"))
    assert row.closed_on is None


def test_a_scheme_must_be_held_with_a_pension_provider():
    with pytest.raises(Refused, match="held with a pension provider"):
        service().open(MANAGER, OpenScheme(
            employer_id="em-1", provider_id="pv-2", code="NEW", name="New",
            employee_basis_points=600, employer_basis_points=400,
            qualifying_floor=130000, opened_on="2025-04-06"))


def test_a_code_the_employer_already_uses_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().open(MANAGER, OpenScheme(
            employer_id="em-1", provider_id="pv-1", code="MAIN", name="Again",
            employee_basis_points=1, employer_basis_points=1,
            qualifying_floor=1, opened_on="2025-04-06"))


def test_a_scheme_is_closed():
    assert service().close(MANAGER, "sc-1", CloseScheme(closed_on="2025-12-31")).closed_on == "2025-12-31"


def test_a_scheme_cannot_be_closed_twice():
    with pytest.raises(Conflict, match="already closed"):
        service().close(MANAGER, "sc-2", CloseScheme(closed_on="2025-12-31"))


def test_a_scheme_cannot_close_before_it_opened():
    with pytest.raises(Refused, match="close before it opened"):
        service().close(MANAGER, "sc-1", CloseScheme(closed_on="2023-01-01"))


def test_the_shares_a_figure_puts_in_are_reported():
    answer = service().shares(MANAGER, "sc-1", 200000)
    assert answer["employee"] == 10000 and answer["total"] == 16000


def test_negative_pensionable_pay_is_refused():
    with pytest.raises(Refused, match="cannot be negative"):
        service().shares(MANAGER, "sc-1", -1)


def client():
    return build_client(a_store())


def test_the_route_lists_schemes():
    assert client().get("/pensions", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_the_shares():
    answer = client().get("/pensions/sc-1/shares?pensionable=200000", headers=headers(MANAGER))
    assert answer.json()["total"] == 16000


def test_the_route_opens_a_scheme_and_answers_201():
    answer = client().post("/pensions", headers=headers(MANAGER), json={
        "employer_id": "em-1", "provider_id": "pv-1", "code": "NEW", "name": "New",
        "employee_basis_points": 600, "employer_basis_points": 400,
        "qualifying_floor": 130000, "opened_on": "2025-04-06"})
    assert answer.status_code == 201


def test_the_route_closes_a_scheme():
    answer = client().post("/pensions/sc-1/close", headers=headers(MANAGER),
                           json={"closed_on": "2025-12-31"})
    assert answer.json()["closed_on"] == "2025-12-31"
