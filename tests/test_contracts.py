"""The terms people are employed on, what they work out to, and how they change."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_contracts, seed_employees,
    seed_employers,
)
from tare.common.types import Contract
from tare.modules.contracts.rules import (
    daily_pay, full_time_part, hourly_pay, in_force_for, in_force_on, service_days,
    service_years, sort_by_start, weekly_pay,
)
from tare.modules.contracts.schemas import ChangeTerms, EndContract, ListContracts, OpenContract
from tare.modules.contracts.service import ContractsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_contracts(store)
    return store


def service():
    return ContractsService(a_store())


def a_contract(**kw) -> Contract:
    base = dict(id="ct-9", employee_id="ee-1", employer_id="em-1",
                started_on="2024-01-01", ended_on=None, hours_per_week=37,
                annual_salary=2600000, notice_weeks=4)
    return Contract(**{**base, **kw})


def test_contracts_read_oldest_first():
    rows = sort_by_start([a_contract(started_on="2024-06-01"), a_contract(started_on="2024-01-01")])
    assert [row.started_on for row in rows] == ["2024-01-01", "2024-06-01"]


def test_a_contract_governs_the_day_it_started():
    assert in_force_on(a_contract(started_on="2024-01-01"), "2024-01-01") is True


def test_a_contract_does_not_govern_the_day_before_it_started():
    assert in_force_on(a_contract(started_on="2024-01-01"), "2023-12-31") is False


def test_a_contract_still_governs_the_day_it_ended():
    row = a_contract(started_on="2024-01-01", ended_on="2024-06-30")
    assert in_force_on(row, "2024-06-30") is True


def test_a_contract_does_not_govern_the_day_after_it_ended():
    row = a_contract(started_on="2024-01-01", ended_on="2024-06-30")
    assert in_force_on(row, "2024-07-01") is False


def test_the_contract_in_force_is_the_one_covering_the_day():
    rows = [a_contract(id="a", started_on="2024-01-01", ended_on="2024-06-30"),
            a_contract(id="b", started_on="2024-07-01")]
    assert in_force_for(rows, "ee-1", "2024-08-01").id == "b"


def test_the_later_start_wins_where_two_contracts_cover_a_day():
    rows = [a_contract(id="a", started_on="2024-01-01"),
            a_contract(id="b", started_on="2024-07-01")]
    assert in_force_for(rows, "ee-1", "2024-08-01").id == "b"


def test_nothing_is_in_force_before_anybody_started():
    assert in_force_for([a_contract(started_on="2024-01-01")], "ee-1", "2023-01-01") is None


def test_another_persons_contract_is_not_in_force_for_this_one():
    assert in_force_for([a_contract(employee_id="ee-2")], "ee-1", "2024-06-01") is None


def test_a_year_of_salary_divides_into_fifty_two_weeks():
    assert weekly_pay(a_contract(annual_salary=2600000)) == 50000


def test_a_week_of_pay_rounds_half_up_rather_than_truncating():
    # 2600050 over 52 is 50000.96, which rounds to 50001 rather than 50000.
    assert weekly_pay(a_contract(annual_salary=2600050)) == 50001


def test_a_day_of_pay_is_a_week_over_seven():
    assert daily_pay(a_contract(annual_salary=2600000)) == 7143


def test_an_hour_of_pay_comes_off_the_contracted_hours():
    assert hourly_pay(a_contract(annual_salary=2600000, hours_per_week=37)) == 1351


def test_a_contract_of_no_hours_has_no_hourly_rate_rather_than_dividing_by_nothing():
    assert hourly_pay(a_contract(hours_per_week=0)) == 0


def test_a_full_week_is_the_whole_part():
    assert full_time_part(a_contract(hours_per_week=37)) == 10000


def test_a_half_week_is_half_the_part():
    assert full_time_part(a_contract(hours_per_week=18)) == 4865


def test_more_than_a_full_week_is_still_only_one_person():
    assert full_time_part(a_contract(hours_per_week=50)) == 10000


def test_service_counts_both_ends():
    assert service_days(a_contract(started_on="2025-04-01"), "2025-04-30") == 30


def test_service_stops_on_the_day_a_contract_ended():
    row = a_contract(started_on="2025-04-01", ended_on="2025-04-10")
    assert service_days(row, "2025-04-30") == 10


def test_service_before_a_contract_started_is_nothing():
    assert service_days(a_contract(started_on="2025-04-01"), "2025-03-01") == 0


def test_service_in_whole_years_counts_at_three_hundred_and_sixty_five_days():
    assert service_years(a_contract(started_on="2024-01-01"), "2024-12-31") == 1


def test_service_a_day_short_of_a_year_is_no_years():
    assert service_years(a_contract(started_on="2025-01-01"), "2025-12-30") == 0


def test_contracts_are_listed():
    assert service().list(BUREAU, ListContracts())["total"] == 4


def test_a_manager_lists_only_their_own_employers_contracts():
    assert service().list(MANAGER, ListContracts())["total"] == 3


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(BUREAU, ListContracts(employee_id="ee-1"))["total"] == 1


def test_a_listing_can_be_narrowed_to_what_was_in_force_on_a_day():
    # Bram's starts in July 2025 and Joss's ended that May, so June leaves
    # Nell's and Wren's standing.
    assert service().list(BUREAU, ListContracts(in_force_on="2025-06-15"))["total"] == 2


def test_a_contract_can_be_read():
    assert service().get(BUREAU, "ct-1").annual_salary == 3120000


def test_a_contract_nobody_has_is_missing():
    with pytest.raises(NotFound, match="contract ct-9 was not found"):
        service().get(BUREAU, "ct-9")


def test_a_manager_cannot_read_another_employers_contract():
    with pytest.raises(Refused):
        service().get(MANAGER, "ct-4")


def test_the_contract_in_force_for_somebody_is_found():
    assert service().in_force(MANAGER, "ee-1", "2025-06-01").id == "ct-1"


def test_nothing_in_force_for_somebody_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="contract in force"):
        service().in_force(MANAGER, "ee-3", "2025-08-01")


def test_a_contract_is_opened_for_somebody_who_has_none():
    row = service().open(MANAGER, OpenContract(
        employee_id="ee-3", started_on="2025-08-01", hours_per_week=30,
        annual_salary=2000000))
    assert row.employer_id == "em-1" and row.ended_on is None


def test_a_contract_cannot_start_before_the_person_joined():
    with pytest.raises(Refused, match="before the person joined"):
        service().open(MANAGER, OpenContract(
            employee_id="ee-2", started_on="2024-01-01", hours_per_week=20,
            annual_salary=1000000))


def test_a_second_contract_over_one_already_standing_is_refused():
    with pytest.raises(Conflict, match="already holds a contract"):
        service().open(MANAGER, OpenContract(
            employee_id="ee-1", started_on="2025-06-01", hours_per_week=37,
            annual_salary=3000000))


def test_a_contract_is_ended():
    assert service() \
        .end(MANAGER, "ct-1", EndContract(ended_on="2025-09-30")).ended_on == "2025-09-30"


def test_a_contract_cannot_end_twice():
    with pytest.raises(Conflict, match="already ended"):
        service().end(MANAGER, "ct-3", EndContract(ended_on="2025-09-30"))


def test_a_contract_cannot_end_before_it_started():
    with pytest.raises(Refused, match="end before it started"):
        service().end(MANAGER, "ct-1", EndContract(ended_on="2019-01-01"))


def test_changing_terms_opens_a_new_contract():
    row = service().change_terms(MANAGER, "ee-1", ChangeTerms(
        from_day="2025-06-01", annual_salary=3300000))
    assert row.started_on == "2025-06-01" and row.annual_salary == 3300000


def test_changing_terms_ends_the_old_contract_the_day_before():
    svc = service()
    svc.change_terms(MANAGER, "ee-1", ChangeTerms(from_day="2025-06-01", annual_salary=3300000))
    assert svc.get(MANAGER, "ct-1").ended_on == "2025-05-31"


def test_terms_not_named_in_a_change_carry_over_unchanged():
    row = service().change_terms(MANAGER, "ee-1", ChangeTerms(
        from_day="2025-06-01", annual_salary=3300000))
    assert row.hours_per_week == 37 and row.notice_weeks == 8


def test_terms_cannot_change_on_the_day_the_contract_started():
    with pytest.raises(Refused, match="the day the contract started"):
        service().change_terms(MANAGER, "ee-2", ChangeTerms(
            from_day="2025-07-01", annual_salary=1600000))


def test_the_figures_a_contract_works_out_to_are_reported_together():
    answer = service().terms(BUREAU, "ct-1", "2025-04-05")
    assert answer["weekly_pay"] == 60000 and answer["full_time_part"] == 10000


def client():
    return build_client(a_store())


def test_the_route_lists_contracts():
    assert client().get("/contracts", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_reads_one_contract():
    assert client().get("/contracts/ct-1", headers=headers(BUREAU)).json()["notice_weeks"] == 8


def test_the_route_reports_what_a_contract_works_out_to():
    answer = client().get("/contracts/ct-1/terms?upto=2025-04-05", headers=headers(BUREAU))
    assert answer.json()["weekly_pay"] == 60000


def test_the_route_opens_a_contract_and_answers_201():
    answer = client().post("/contracts", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "started_on": "2025-08-01", "hours_per_week": 30,
        "annual_salary": 2000000})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_contract_over_one_already_standing():
    answer = client().post("/contracts", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "started_on": "2025-06-01", "hours_per_week": 37,
        "annual_salary": 3000000})
    assert answer.status_code == 409


def test_the_route_changes_terms():
    answer = client().post("/contracts/of/ee-1/terms", headers=headers(MANAGER),
                           json={"from_day": "2025-06-01", "annual_salary": 3300000})
    assert answer.json()["annual_salary"] == 3300000


def test_the_route_refuses_hours_beyond_what_a_week_holds():
    answer = client().post("/contracts", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "started_on": "2025-08-01", "hours_per_week": 200,
        "annual_salary": 2000000})
    assert answer.status_code == 422
