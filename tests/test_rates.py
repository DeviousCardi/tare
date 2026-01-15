"""Rates: what one person is paid for one element, and what it comes to."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_contracts, seed_elements,
    seed_employees, seed_employers, seed_rates,
)
from tare.common.types import PayRate
from tare.modules.rates.rules import amount_for, for_element, is_hours_based
from tare.modules.rates.schemas import ListRates, SetRate
from tare.modules.rates.service import RatesService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_contracts(store)
    seed_elements(store)
    seed_rates(store)
    return store


def service():
    return RatesService(a_store())


def a_rate(**kw) -> PayRate:
    base = dict(id="rt-9", employee_id="ee-1", employer_id="em-1", element_id="el-1",
                basis="fixed", amount=260000, effective_from="2024-04-06")
    return PayRate(**{**base, **kw})


def test_the_rate_in_force_is_the_latest_already_taken_effect():
    assert for_element(a_store().rates.all(), "ee-1", "el-1", "2025-06-01").amount == 268000


def test_a_rate_takes_effect_on_its_own_date():
    assert for_element(a_store().rates.all(), "ee-1", "el-1", "2025-04-06").amount == 268000


def test_the_day_before_a_change_still_reads_the_older_rate():
    assert for_element(a_store().rates.all(), "ee-1", "el-1", "2025-04-05").amount == 260000


def test_a_rate_for_another_element_is_not_in_force_for_this_one():
    assert for_element(a_store().rates.all(), "ee-2", "el-2", "2025-08-01") is None


def test_a_rate_before_it_was_set_is_not_in_force():
    assert for_element(a_store().rates.all(), "ee-2", "el-1", "2025-01-01") is None


def test_a_fixed_rate_is_its_own_amount_whatever_the_hours():
    assert amount_for(a_rate(basis="fixed", amount=260000), 0, 1351) == 260000


def test_a_fixed_rate_ignores_the_hours_entirely():
    assert amount_for(a_rate(basis="fixed", amount=260000), 40, 1351) == 260000


def test_an_hourly_rate_is_its_amount_for_each_hour():
    assert amount_for(a_rate(basis="hourly", amount=1400), 10, 0) == 14000


def test_an_hourly_rate_over_no_hours_comes_to_nothing():
    assert amount_for(a_rate(basis="hourly", amount=1400), 0, 0) == 0


def test_a_multiple_is_a_share_of_the_contracts_own_hourly_rate():
    # Time and a half of 1000 an hour, over four hours.
    assert amount_for(a_rate(basis="multiple", amount=15000), 4, 1000) == 6000


def test_a_multiple_of_the_whole_is_the_hourly_rate_itself():
    assert amount_for(a_rate(basis="multiple", amount=10000), 3, 1000) == 3000


def test_negative_hours_come_to_nothing_rather_than_taking_pay_away():
    assert amount_for(a_rate(basis="hourly", amount=1400), -5, 0) == 0


def test_an_hourly_rate_needs_hours():
    assert is_hours_based(a_rate(basis="hourly")) is True


def test_a_multiple_needs_hours():
    assert is_hours_based(a_rate(basis="multiple")) is True


def test_a_fixed_rate_needs_no_hours():
    assert is_hours_based(a_rate(basis="fixed")) is False


def test_the_bureau_lists_every_rate():
    assert service().list(BUREAU, ListRates())["total"] == 4


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListRates(employee_id="ee-1"))["total"] == 3


def test_a_listing_can_be_narrowed_to_what_is_in_force():
    assert service().list(MANAGER, ListRates(in_force_on="2025-06-01"))["total"] == 2


def test_a_rate_can_be_read():
    assert service().get(MANAGER, "rt-1").basis == "fixed"


def test_a_rate_nobody_set_is_missing():
    with pytest.raises(NotFound, match="rate rt-9 was not found"):
        service().get(BUREAU, "rt-9")


def test_the_rate_in_force_is_reported():
    assert service().in_force(MANAGER, "ee-1", "el-1", "2025-06-01").amount == 268000


def test_a_rate_in_force_nowhere_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="rate in force"):
        service().in_force(MANAGER, "ee-2", "el-2", "2025-08-01")


def test_a_rate_is_set():
    row = service().set(MANAGER, SetRate(
        employee_id="ee-2", element_id="el-2", basis="multiple", amount=15000,
        effective_from="2025-07-01"))
    assert row.basis == "multiple"


def test_a_basis_a_rate_is_not_quoted_on_is_refused():
    with pytest.raises(Refused, match="is not a basis a rate is quoted on"):
        service().set(MANAGER, SetRate(
            employee_id="ee-2", element_id="el-2", basis="guess", amount=1,
            effective_from="2025-07-01"))


def test_a_rate_cannot_name_another_employers_element():
    with pytest.raises(Refused, match="person's own employer"):
        service().set(BUREAU, SetRate(
            employee_id="ee-1", element_id="el-5", basis="fixed", amount=1,
            effective_from="2025-07-01"))


def test_one_rate_cannot_change_twice_on_a_day():
    with pytest.raises(Conflict, match="already changes on"):
        service().set(MANAGER, SetRate(
            employee_id="ee-1", element_id="el-1", basis="fixed", amount=1,
            effective_from="2025-04-06"))


def test_what_a_rate_comes_to_for_a_run_of_hours_is_reported():
    answer = service().applied(MANAGER, "ee-1", "el-2", "2025-06-01", 4)
    assert answer["amount"] == 9732


def test_negative_hours_are_refused():
    with pytest.raises(Refused, match="hours cannot be negative"):
        service().applied(MANAGER, "ee-1", "el-2", "2025-06-01", -1)


def client():
    return build_client(a_store())


def test_the_route_lists_rates():
    assert client().get("/rates", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reports_what_a_rate_comes_to():
    answer = client().get("/rates/applied/ee-1?element_id=el-2&on=2025-06-01&hours=4",
                          headers=headers(MANAGER))
    assert answer.json()["amount"] == 9732


def test_the_route_sets_a_rate_and_answers_201():
    answer = client().post("/rates", headers=headers(MANAGER), json={
        "employee_id": "ee-2", "element_id": "el-2", "basis": "multiple",
        "amount": 15000, "effective_from": "2025-07-01"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_rate_already_changing_that_day():
    answer = client().post("/rates", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "element_id": "el-1", "basis": "fixed",
        "amount": 1, "effective_from": "2025-04-06"})
    assert answer.status_code == 409
