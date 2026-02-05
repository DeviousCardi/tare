"""Registers: what a committed run looks like, gathered up."""

import pytest

from tare.common.errors import NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_cost_centres,
    seed_departments, seed_employees, seed_employers, seed_payslips, seed_positions,
)
from tare.common.types import Payslip
from tare.modules.registers.rules import gather, totals_of, worth_showing
from tare.modules.registers.service import RegistersService
from tare.common.types import PayrollRun


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_departments, seed_cost_centres,
                 seed_positions, seed_payslips):
        seed(store)
    for run_id, employer_id, period in (("rn-1", "em-1", 1), ("rn-2", "em-1", 2),
                                        ("rn-3", "em-2", 1)):
        store.runs.insert(PayrollRun(
            id=run_id, employer_id=employer_id, calendar_id="pc-1", period=period,
            status="committed", opened_on="2025-05-06", committed_on="2025-05-07"))
    return store


def service():
    return RegistersService(a_store())


def a_slip(**kw) -> Payslip:
    base = dict(id="ps-slip-9", run_id="rn-1", employee_id="ee-1", employer_id="em-1",
                period=1, start="2025-04-06", end="2025-05-05", gross=268000,
                taxable=268000, free_pay=108000, levy=32000, contributory=268000,
                contributions=12800, deductions=1500, net=221700)
    return Payslip(**{**base, **kw})


# Every payslip below carries a net figure of its own, which is what an
# ordinary run produces, so what appears on the register does not depend on how
# a payslip that nets to nothing is treated.
def test_a_payslip_that_paid_something_belongs_on_a_register():
    assert worth_showing(a_slip(net=221700)) is True


def test_payslips_gather_into_one_line_for_each_key():
    lines = gather([a_slip(id="a", employee_id="ee-1"),
                    a_slip(id="b", employee_id="ee-2")], lambda row: row.employee_id)
    assert [line.key for line in lines] == ["ee-1", "ee-2"]


def test_two_payslips_for_one_key_fold_into_one_line():
    lines = gather([a_slip(id="a"), a_slip(id="b")], lambda row: "one")
    assert len(lines) == 1 and lines[0].gross == 536000


def test_a_gathered_line_counts_each_person_once():
    lines = gather([a_slip(id="a"), a_slip(id="b")], lambda row: "one")
    assert lines[0].headcount == 1


def test_a_gathered_line_counts_two_people_as_two():
    lines = gather([a_slip(id="a", employee_id="ee-1"),
                    a_slip(id="b", employee_id="ee-2")], lambda row: "one")
    assert lines[0].headcount == 2


def test_lines_read_in_key_order():
    lines = gather([a_slip(id="a", employee_id="ee-2"),
                    a_slip(id="b", employee_id="ee-1")], lambda row: row.employee_id)
    assert [line.key for line in lines] == ["ee-1", "ee-2"]


def test_no_payslips_gather_to_no_lines():
    assert gather([], lambda row: "one") == []


def test_the_bottom_line_adds_the_lines_up():
    lines = gather([a_slip(id="a", employee_id="ee-1"),
                    a_slip(id="b", employee_id="ee-2")], lambda row: row.employee_id)
    assert totals_of(lines).gross == 536000


def test_the_bottom_line_counts_everybody():
    lines = gather([a_slip(id="a", employee_id="ee-1"),
                    a_slip(id="b", employee_id="ee-2")], lambda row: row.employee_id)
    assert totals_of(lines).headcount == 2


def test_a_register_of_no_lines_bottoms_out_at_nothing():
    assert totals_of([]).net == 0


def test_a_register_gathers_a_run_by_person():
    answer = service().of(MANAGER, "rn-2", "employee")
    assert [line["key"] for line in answer["lines"]] == ["ee-1"]


def test_a_register_gathers_a_run_by_department():
    answer = service().of(MANAGER, "rn-2", "department")
    assert answer["lines"][0]["key"] == "dp-2"


def test_a_register_gathers_a_run_by_cost_centre():
    answer = service().of(MANAGER, "rn-2", "cost_centre")
    assert answer["lines"][0]["key"] == "cc-1"


def test_a_register_carries_the_run_it_was_read_from():
    assert service().of(MANAGER, "rn-2", "employee")["run_id"] == "rn-2"


def test_a_register_bottoms_out_at_what_the_run_paid():
    answer = service().of(MANAGER, "rn-2", "employee")
    assert answer["totals"]["net"] == 248555


def test_a_register_carries_what_the_run_owed_the_revenue():
    answer = service().of(MANAGER, "rn-2", "employee")
    assert answer["totals"]["levy"] == 11860


def test_a_grouping_a_register_does_not_know_is_refused():
    with pytest.raises(Refused, match="cannot be gathered by"):
        service().of(MANAGER, "rn-2", "star sign")


def test_a_run_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="run rn-99 was not found"):
        service().of(BUREAU, "rn-99", "employee")


def test_a_manager_cannot_read_another_employers_register():
    with pytest.raises(Refused):
        service().of(MANAGER, "rn-3", "employee")


def client():
    return build_client(a_store())


def test_the_route_reports_a_register():
    answer = client().get("/registers/rn-2", headers=headers(MANAGER))
    assert answer.json()["totals"]["net"] == 248555


def test_the_route_gathers_a_register_by_department():
    answer = client().get("/registers/rn-2?grouped_by=department", headers=headers(MANAGER))
    assert answer.json()["lines"][0]["key"] == "dp-2"


def test_the_route_answers_400_for_a_grouping_it_does_not_know():
    answer = client().get("/registers/rn-2?grouped_by=nonsense", headers=headers(MANAGER))
    assert answer.status_code == 400


def test_the_route_answers_404_for_a_run_nobody_opened():
    assert client().get("/registers/rn-99", headers=headers(BUREAU)).status_code == 404
