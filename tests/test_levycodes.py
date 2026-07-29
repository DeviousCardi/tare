"""Levy codes, and the free pay each one gives as the year runs on."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_levy_codes,
)
from tare.common.types import LevyCode
from tare.modules.levycodes.rules import (
    every_code_on, for_code, free_pay_for_period, is_cumulative,
)
from tare.modules.levycodes.schemas import ListLevyCodes, PublishLevyCode
from tare.modules.levycodes.service import LevyCodesService


def a_store():
    store = build_store()
    seed_levy_codes(store)
    return store


def service():
    return LevyCodesService(a_store())


def a_code(**kw) -> LevyCode:
    base = dict(id="lc-9", code="L1", description="Ordinary", annual_allowance=1257000,
                basis="cumulative", effective_from="2024-04-06")
    return LevyCode(**{**base, **kw})


def test_a_cumulative_code_is_cumulative():
    assert is_cumulative(a_code(basis="cumulative")) is True


def test_a_period_code_is_not_cumulative():
    assert is_cumulative(a_code(basis="period")) is False


def test_the_version_of_a_code_in_force_is_the_latest_already_taken_effect():
    assert for_code(a_store().levy_codes.all(), "L1", "2025-06-01").id == "lc-2"


def test_a_code_takes_effect_on_its_own_date():
    assert for_code(a_store().levy_codes.all(), "L1", "2025-04-06").id == "lc-2"


def test_the_day_before_a_change_still_reads_the_older_version():
    assert for_code(a_store().levy_codes.all(), "L1", "2025-04-05").id == "lc-1"


def test_a_code_nobody_published_is_not_in_force():
    assert for_code(a_store().levy_codes.all(), "L9", "2025-06-01") is None


def test_a_code_is_not_in_force_before_it_was_published():
    assert for_code(a_store().levy_codes.all(), "L1", "2020-01-01") is None


def test_every_code_in_force_on_a_day_is_found_at_once():
    found = every_code_on(a_store().levy_codes.all(), "2025-06-01")
    assert sorted(row.code for row in found) == ["L1", "L2"]


def test_a_cumulative_code_gives_one_share_by_the_first_period():
    assert free_pay_for_period(a_code(annual_allowance=1200000), "monthly", 1) == 100000


def test_a_cumulative_code_has_given_six_shares_by_the_sixth_period():
    assert free_pay_for_period(a_code(annual_allowance=1200000), "monthly", 6) == 600000


def test_a_cumulative_code_gives_the_whole_allowance_by_the_last_period():
    assert free_pay_for_period(a_code(annual_allowance=1257000), "monthly", 12) == 1257000


def test_a_period_code_gives_only_its_own_periods_share():
    row = a_code(basis="period", annual_allowance=1200000)
    assert free_pay_for_period(row, "monthly", 6) == 100000


def test_a_year_of_a_period_code_still_comes_to_the_allowance():
    row = a_code(basis="period", annual_allowance=1257000)
    assert sum(free_pay_for_period(row, "monthly", n) for n in range(1, 13)) == 1257000


def test_a_weekly_payroll_splits_the_allowance_fifty_two_ways():
    assert free_pay_for_period(a_code(annual_allowance=5200000), "weekly", 1) == 100000


def test_a_fortnightly_payroll_splits_the_allowance_twenty_six_ways():
    assert free_pay_for_period(a_code(annual_allowance=2600000), "fortnightly", 1) == 100000


def test_an_allowance_that_does_not_divide_evenly_still_comes_to_itself():
    row = a_code(annual_allowance=1000)
    assert free_pay_for_period(row, "monthly", 12) == 1000


def test_a_period_before_the_year_starts_gives_nothing():
    assert free_pay_for_period(a_code(), "monthly", 0) == 0


def test_a_period_past_the_end_of_the_year_gives_nothing():
    assert free_pay_for_period(a_code(), "monthly", 13) == 0


def test_a_code_carrying_no_allowance_gives_nothing_all_year():
    assert free_pay_for_period(a_code(annual_allowance=0), "monthly", 12) == 0


def test_codes_are_listed():
    assert service().list(MANAGER, ListLevyCodes())["total"] == 3


def test_a_listing_can_be_narrowed_to_one_code():
    assert service().list(MANAGER, ListLevyCodes(code="L1"))["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_in_force_on_a_day():
    assert service().list(MANAGER, ListLevyCodes(in_force_on="2025-06-01"))["total"] == 2


def test_a_row_can_be_read():
    assert service().get(MANAGER, "lc-1").annual_allowance == 1257000


def test_a_row_nobody_published_is_missing():
    with pytest.raises(NotFound, match="levy code lc-9 was not found"):
        service().get(MANAGER, "lc-9")


def test_the_code_in_force_is_found():
    assert service().in_force("L1", "2025-06-01").annual_allowance == 1296000


def test_a_code_in_force_nowhere_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="levy code in force"):
        service().in_force("L9", "2025-06-01")


def test_the_bureau_publishes_a_code():
    row = service().publish(BUREAU, PublishLevyCode(
        code="L3", description="Third", annual_allowance=500000,
        basis="period", effective_from="2026-04-06"))
    assert row.code == "L3"


def test_nobody_but_the_bureau_publishes_a_code():
    with pytest.raises(Refused, match="only the bureau may publish a levy code"):
        service().publish(MANAGER, PublishLevyCode(
            code="L3", description="Third", annual_allowance=0,
            basis="period", effective_from="2026-04-06"))


def test_a_basis_the_service_does_not_work_on_is_refused():
    with pytest.raises(Refused, match="is not a basis"):
        service().publish(BUREAU, PublishLevyCode(
            code="L3", description="Third", annual_allowance=0,
            basis="guesswork", effective_from="2026-04-06"))


def test_a_second_change_to_one_code_on_one_day_is_refused():
    with pytest.raises(Conflict, match="already changes on"):
        service().publish(BUREAU, PublishLevyCode(
            code="L1", description="Again", annual_allowance=1, basis="cumulative",
            effective_from="2025-04-06"))


def test_a_published_code_takes_effect_from_its_own_day():
    svc = service()
    svc.publish(BUREAU, PublishLevyCode(
        code="L1", description="Raised", annual_allowance=1400000,
        basis="cumulative", effective_from="2026-04-06"))
    assert svc.in_force("L1", "2026-04-06").annual_allowance == 1400000


def test_a_frequency_the_service_does_not_run_is_refused():
    with pytest.raises(Refused, match="is not a frequency"):
        service().free_pay("L1", "2025-06-01", "daily", 1)


def test_the_free_pay_a_code_gives_is_reported():
    assert service().free_pay("L1", "2025-06-01", "monthly", 12)["free_pay"] == 1296000


def client():
    return build_client(a_store())


def test_the_route_lists_codes():
    assert client().get("/levy-codes", headers=headers(MANAGER)).json()["total"] == 3


def test_the_route_reports_free_pay():
    answer = client().get("/levy-codes/L1/free-pay?on=2025-06-01&frequency=monthly&period=12",
                          headers=headers(MANAGER))
    assert answer.json()["free_pay"] == 1296000


def test_the_route_answers_404_for_a_code_in_force_nowhere():
    answer = client().get("/levy-codes/L9/free-pay?on=2025-06-01&frequency=monthly&period=1",
                          headers=headers(MANAGER))
    assert answer.status_code == 404


def test_the_route_publishes_a_code_and_answers_201():
    answer = client().post("/levy-codes", headers=headers(BUREAU), json={
        "code": "L3", "description": "Third", "annual_allowance": 0,
        "basis": "period", "effective_from": "2026-04-06"})
    assert answer.status_code == 201


def test_the_route_answers_400_when_a_manager_publishes():
    answer = client().post("/levy-codes", headers=headers(MANAGER), json={
        "code": "L3", "description": "Third", "annual_allowance": 0,
        "basis": "period", "effective_from": "2026-04-06"})
    assert answer.status_code == 400
