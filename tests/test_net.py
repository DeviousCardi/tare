"""Net pay: working a gross figure down to what is handed over."""

import pytest

from tare.common.errors import Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_bands, seed_calendars,
    seed_contracts, seed_deductions, seed_elements, seed_employees, seed_employers,
    seed_exemptions, seed_levy_codes, seed_rates, seed_timesheets,
)
from tare.modules.net.rules import Worked, assemble, levyable_pay, net_pay, take_home_share
from tare.modules.net.service import NetService


def a_store(with_exemptions: bool = False):
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_contracts, seed_elements,
                 seed_rates, seed_calendars, seed_timesheets, seed_levy_codes,
                 seed_bands, seed_deductions):
        seed(store)
    if with_exemptions:
        seed_exemptions(store)
    return store


def service(with_exemptions: bool = False):
    return NetService(a_store(with_exemptions))


def test_free_pay_comes_off_before_the_levy_is_worked_out():
    assert levyable_pay(275299, 216000) == 59299


def test_free_pay_larger_than_the_taxable_figure_leaves_nothing_to_charge():
    assert levyable_pay(50000, 216000) == 0


def test_nothing_taxable_leaves_nothing_to_charge():
    assert levyable_pay(0, 216000) == 0


def test_net_is_the_gross_less_everything_taken_off_it():
    assert net_pay(275299, 11860, 13384, 1500) == 248555


def test_net_reaches_nothing_but_never_goes_below_it():
    assert net_pay(1000, 500, 500, 500) == 0


def test_a_gross_of_nothing_nets_nothing():
    assert net_pay(0, 0, 0, 0) == 0


def test_the_share_taken_home_is_reported_in_basis_points():
    worked = assemble(gross=100000, taxable=100000, free_pay=0, levy=20000,
                      contributory=100000, contributions=0, deductions=0)
    assert take_home_share(worked) == 8000


def test_no_gross_takes_home_no_share_rather_than_dividing_by_nothing():
    worked = assemble(gross=0, taxable=0, free_pay=0, levy=0, contributory=0,
                      contributions=0, deductions=0)
    assert take_home_share(worked) == 0


def test_assembling_works_the_levyable_figure_out_for_itself():
    worked = assemble(gross=275299, taxable=275299, free_pay=216000, levy=11860,
                      contributory=275299, contributions=13384, deductions=1500)
    assert worked.levyable == 59299 and worked.net == 248555


def test_a_period_works_all_the_way_down_to_net():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert answer["gross"] == 275299 and answer["net"] == 248555


def test_the_free_pay_the_levy_code_gives_comes_off_the_taxable_figure():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert answer["free_pay"] == 216000 and answer["levyable"] == 59299


def test_the_levy_is_charged_on_what_is_left_after_free_pay():
    assert service().of(MANAGER, "ee-1", "pc-1", 2)["levy"] == 11860


def test_contributions_are_charged_on_their_own_figure():
    assert service().of(MANAGER, "ee-1", "pc-1", 2)["contributions"] == 13384


def test_deductions_come_out_of_what_is_left_after_the_revenue():
    assert service().of(MANAGER, "ee-1", "pc-1", 2)["deductions"] == 1500


def test_the_deduction_lines_say_what_each_instruction_took():
    lines = service().of(MANAGER, "ee-1", "pc-1", 2)["deduction_lines"]
    assert lines == [{"element_id": "el-4", "asked": 1500, "taken": 1500, "short": 0}]


def test_the_payment_lines_come_through_from_the_gross():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert [line["code"] for line in answer["lines"]] == ["BASIC", "OT"]


def test_somebody_exempt_from_contributions_is_charged_none():
    assert service(with_exemptions=True).of(MANAGER, "ee-1", "pc-1", 2)["contributions"] == 0


def test_an_exemption_from_contributions_leaves_the_levy_alone():
    assert service(with_exemptions=True).of(MANAGER, "ee-1", "pc-1", 2)["levy"] == 11860


def test_an_exemption_from_contributions_leaves_more_to_take_home():
    assert service(with_exemptions=True).of(MANAGER, "ee-1", "pc-1", 2)["net"] == 261939


def test_a_period_with_no_hours_still_pays_the_fixed_rate_down_to_net():
    answer = service().of(MANAGER, "ee-1", "pc-1", 3)
    assert answer["gross"] == 268000 and answer["net"] < answer["gross"]


def test_the_window_the_period_covers_comes_through():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert answer["start"] == "2025-05-06" and answer["end"] == "2025-06-05"


def test_a_calendar_belonging_to_another_employer_is_refused():
    with pytest.raises(Refused, match="belongs to another employer"):
        service().of(BUREAU, "ee-1", "pc-3", 2)


def test_a_manager_cannot_work_out_another_employers_net():
    with pytest.raises(Refused):
        service().of(MANAGER, "ee-4", "pc-3", 2)


def client(with_exemptions: bool = False):
    return build_client(a_store(with_exemptions))


def test_the_route_reports_net_pay():
    answer = client().get("/net/ee-1?calendar_id=pc-1&period=2", headers=headers(MANAGER))
    assert answer.json()["net"] == 248555


def test_the_route_reports_every_figure_on_the_way_down():
    answer = client().get("/net/ee-1?calendar_id=pc-1&period=2", headers=headers(MANAGER))
    body = answer.json()
    assert body["levy"] == 11860 and body["contributions"] == 13384


def test_the_route_honours_an_exemption():
    answer = client(True).get("/net/ee-1?calendar_id=pc-1&period=2", headers=headers(MANAGER))
    assert answer.json()["contributions"] == 0


def test_the_route_answers_400_for_a_period_outside_the_year():
    answer = client().get("/net/ee-1?calendar_id=pc-1&period=13", headers=headers(MANAGER))
    assert answer.status_code == 400
