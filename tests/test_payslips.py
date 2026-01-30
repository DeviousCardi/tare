"""Payslips: what somebody was paid, and what the year has come to."""

import pytest

from tare.common.errors import NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_payslips,
)
from tare.common.types import Payslip, PayslipLine
from tare.modules.payslips.rules import (
    balances, lines_come_to, sort_by_period, sort_lines, year_to_date,
)
from tare.modules.payslips.schemas import ListPayslips
from tare.modules.payslips.service import PayslipsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_payslips(store)
    return store


def service():
    return PayslipsService(a_store())


def a_payslip(**kw) -> Payslip:
    base = dict(id="ps-slip-9", run_id="rn-9", employee_id="ee-1", employer_id="em-1",
                period=1, start="2025-04-06", end="2025-05-05", gross=268000,
                taxable=268000, free_pay=108000, levy=32000, contributory=268000,
                contributions=12800, deductions=1500, net=221700)
    return Payslip(**{**base, **kw})


def a_line(**kw) -> PayslipLine:
    base = dict(id="pl-9", payslip_id="ps-slip-1", element_id="el-1",
                kind="payment", hours=0, amount=268000)
    return PayslipLine(**{**base, **kw})


def test_payslips_read_earliest_period_first():
    rows = sort_by_period([a_payslip(period=2), a_payslip(period=1)])
    assert [row.period for row in rows] == [1, 2]


def test_lines_read_payments_before_deductions():
    rows = sort_lines([a_line(id="b", kind="deduction", element_id="el-4"),
                       a_line(id="a", kind="payment", element_id="el-1")])
    assert [row.kind for row in rows] == ["payment", "deduction"]


def test_payments_read_in_element_order_among_themselves():
    rows = sort_lines([a_line(id="b", element_id="el-2"),
                       a_line(id="a", element_id="el-1")])
    assert [row.element_id for row in rows] == ["el-1", "el-2"]


def test_a_payslip_whose_figures_come_back_to_its_net_balances():
    assert balances(a_payslip()) is True


def test_a_payslip_whose_net_does_not_follow_its_figures_does_not_balance():
    assert balances(a_payslip(net=999)) is False


def test_the_payments_on_a_payslip_are_added_up():
    rows = [a_line(amount=268000), a_line(id="b", element_id="el-2", amount=7299)]
    assert lines_come_to(rows, "payment") == 275299


def test_the_deductions_on_a_payslip_are_added_up():
    rows = [a_line(amount=268000),
            a_line(id="b", kind="deduction", element_id="el-4", amount=1500)]
    assert lines_come_to(rows, "deduction") == 1500


def test_a_payslip_with_no_deductions_comes_to_nothing_for_them():
    assert lines_come_to([a_line()], "deduction") == 0


def test_the_year_to_date_adds_the_periods_so_far():
    mine = [row for row in a_store().payslips.all() if row.employee_id == "ee-1"]
    assert year_to_date(mine, 2)["gross"] == 543299


def test_the_year_to_date_stops_at_the_period_it_was_asked_for():
    mine = [row for row in a_store().payslips.all() if row.employee_id == "ee-1"]
    assert year_to_date(mine, 1)["gross"] == 268000


def test_the_year_to_date_carries_every_figure_a_payslip_holds():
    mine = [row for row in a_store().payslips.all() if row.employee_id == "ee-1"]
    answer = year_to_date(mine, 2)
    assert answer["levy"] == 43860 and answer["net"] == 470255


def test_a_year_with_nothing_paid_yet_comes_to_nothing():
    assert year_to_date([], 12)["gross"] == 0


def test_the_bureau_lists_every_payslip():
    assert service().list(BUREAU, ListPayslips())["total"] == 3


def test_a_manager_lists_only_their_own_employers_payslips():
    assert service().list(MANAGER, ListPayslips())["total"] == 2


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListPayslips(employee_id="ee-1"))["total"] == 2


def test_a_listing_can_be_narrowed_to_a_period():
    assert service().list(BUREAU, ListPayslips(period=1))["total"] == 2


def test_a_listing_can_be_narrowed_to_a_run():
    assert service().list(MANAGER, ListPayslips(run_id="rn-2"))["total"] == 1


def test_a_payslip_can_be_read():
    assert service().get(MANAGER, "ps-slip-2").net == 248555


def test_a_payslip_nobody_wrote_is_missing():
    with pytest.raises(NotFound, match="payslip ps-slip-9 was not found"):
        service().get(BUREAU, "ps-slip-9")


def test_a_manager_cannot_read_another_employers_payslip():
    with pytest.raises(Refused):
        service().get(MANAGER, "ps-slip-3")


def test_the_lines_behind_a_payslip_are_read():
    assert len(service().lines(MANAGER, "ps-slip-2")) == 3


def test_a_payslip_with_no_lines_reads_none():
    assert service().lines(MANAGER, "ps-slip-1") != []


def test_a_payslip_reads_back_with_its_lines_and_its_totals():
    answer = service().with_lines(MANAGER, "ps-slip-2")
    assert answer["payments"] == 275299 and answer["deductions"] == 1500


def test_a_payslip_read_with_its_lines_says_whether_it_balances():
    assert service().with_lines(MANAGER, "ps-slip-2")["balances"] is True


def test_the_year_to_date_is_reported():
    assert service().year_to_date(MANAGER, "ee-1", 2)["net"] == 470255


def client():
    return build_client(a_store())


def test_the_route_lists_payslips():
    assert client().get("/payslips", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reads_one_payslip():
    assert client().get("/payslips/ps-slip-2", headers=headers(MANAGER)).json()["net"] == 248555


def test_the_route_reads_a_payslip_with_its_lines():
    answer = client().get("/payslips/ps-slip-2/lines", headers=headers(MANAGER))
    assert len(answer.json()["lines"]) == 3


def test_the_route_reports_the_year_to_date():
    answer = client().get("/payslips/year-to-date/ee-1?upto_period=2",
                          headers=headers(MANAGER))
    assert answer.json()["gross"] == 543299


def test_the_route_answers_404_for_a_payslip_nobody_wrote():
    assert client().get("/payslips/ps-slip-9", headers=headers(BUREAU)).status_code == 404
