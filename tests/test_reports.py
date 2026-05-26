"""Reports: the figures a bureau is asked for across everything else."""

import pytest

from tare.common.errors import Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_payslips,
)
from tare.common.types import Payslip
from tare.modules.reports.rules import (
    by_period, cost_of_employment, headcount_by_period, owed_to_revenue, paid_out,
)
from tare.modules.reports.service import ReportsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_payslips):
        seed(store)
    return store


def service():
    return ReportsService(a_store())


def a_slip(**kw) -> Payslip:
    base = dict(id="ps-slip-9", run_id="rn-1", employee_id="ee-1", employer_id="em-1",
                period=1, start="2025-04-06", end="2025-05-05", gross=268000,
                taxable=268000, free_pay=108000, levy=32000, contributory=268000,
                contributions=12800, deductions=1500, net=221700)
    return Payslip(**{**base, **kw})


def test_the_cost_of_employment_is_what_people_earned():
    assert cost_of_employment([a_slip(gross=268000), a_slip(id="b", gross=275299)]) == 543299


def test_no_payslips_cost_nothing():
    assert cost_of_employment([]) == 0


def test_what_is_owed_the_revenue_takes_in_both_charges():
    assert owed_to_revenue([a_slip(levy=32000, contributions=12800)]) == 44800


def test_what_was_paid_out_is_the_net_figures():
    assert paid_out([a_slip(net=221700), a_slip(id="b", net=248555)]) == 470255


def test_each_period_comes_to_its_own_figure():
    rows = [a_slip(id="a", period=1, gross=268000),
            a_slip(id="b", period=2, gross=275299)]
    assert by_period(rows) == {1: 268000, 2: 275299}


def test_two_payslips_in_one_period_fold_together():
    rows = [a_slip(id="a", period=1, gross=1000), a_slip(id="b", period=1, gross=500)]
    assert by_period(rows) == {1: 1500}


def test_a_period_counts_each_person_once():
    rows = [a_slip(id="a", period=1, employee_id="ee-1"),
            a_slip(id="b", period=1, employee_id="ee-1")]
    assert headcount_by_period(rows) == {1: 1}


def test_a_period_counts_two_people_as_two():
    rows = [a_slip(id="a", period=1, employee_id="ee-1"),
            a_slip(id="b", period=1, employee_id="ee-2")]
    assert headcount_by_period(rows) == {1: 2}


def test_no_payslips_report_no_periods():
    assert by_period([]) == {} and headcount_by_period([]) == {}


def test_the_wage_bill_for_an_employer_is_reported():
    answer = service().wage_bill(MANAGER, "em-1")
    assert answer["cost"] == 543299 and answer["paid"] == 470255


def test_the_wage_bill_breaks_down_by_period():
    assert service().wage_bill(MANAGER, "em-1")["by_period"] == {1: 268000, 2: 275299}


def test_the_wage_bill_carries_what_is_owed_the_revenue():
    assert service().wage_bill(MANAGER, "em-1")["revenue"] == 70044


def test_an_employer_with_no_payslips_has_a_wage_bill_of_nothing():
    store = build_store()
    seed_employers(store)
    assert ReportsService(store).wage_bill(BUREAU, "em-1")["cost"] == 0


def test_a_manager_cannot_read_another_employers_wage_bill():
    with pytest.raises(Refused):
        service().wage_bill(MANAGER, "em-2")


def test_the_route_reports_a_wage_bill():
    client = build_client(a_store())
    answer = client.get("/reports/wage-bill/em-1", headers=headers(MANAGER))
    assert answer.json()["cost"] == 543299
