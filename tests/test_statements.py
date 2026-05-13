"""Statements: what somebody was paid across a whole year."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_payslips,
)
from tare.common.types import Payslip, YearEndStatement
from tare.modules.statements.rules import (
    agrees_with, is_issued, sort_by_year, take_home_share, totals_from,
)
from tare.modules.statements.schemas import DrawStatement, IssueStatement, ListStatements
from tare.modules.statements.service import StatementsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_payslips):
        seed(store)
    return store


def service():
    return StatementsService(a_store())


def a_statement(**kw) -> YearEndStatement:
    base = dict(id="ys-9", employee_id="ee-1", employer_id="em-1",
                year_starts_on="2025-04-06", year_ends_on="2026-04-05",
                gross=543299, levy=43860, contributions=26184, net=470255,
                issued_on=None)
    return YearEndStatement(**{**base, **kw})


def a_slip(**kw) -> Payslip:
    base = dict(id="ps-slip-9", run_id="rn-1", employee_id="ee-1", employer_id="em-1",
                period=1, start="2025-04-06", end="2025-05-05", gross=268000,
                taxable=268000, free_pay=108000, levy=32000, contributory=268000,
                contributions=12800, deductions=1500, net=221700)
    return Payslip(**{**base, **kw})


def test_statements_read_by_year():
    rows = sort_by_year([a_statement(year_starts_on="2025-04-06"),
                         a_statement(year_starts_on="2024-04-06")])
    assert [row.year_starts_on for row in rows] == ["2024-04-06", "2025-04-06"]


def test_a_statement_nobody_issued_is_not_issued():
    assert is_issued(a_statement(issued_on=None)) is False


def test_an_issued_statement_is_issued():
    assert is_issued(a_statement(issued_on="2026-05-31")) is True


def test_the_totals_add_the_payslips_up():
    totals = totals_from([a_slip(gross=268000, net=221700),
                          a_slip(id="b", gross=275299, net=248555)])
    assert totals["gross"] == 543299 and totals["net"] == 470255


def test_a_year_with_no_payslips_totals_nothing():
    assert totals_from([])["gross"] == 0


def test_a_statement_matching_its_payslips_agrees_with_them():
    slips = [a_slip(gross=268000, levy=32000, contributions=12800, net=221700)]
    row = a_statement(gross=268000, levy=32000, contributions=12800, net=221700)
    assert agrees_with(row, slips) is True


def test_a_statement_that_has_drifted_does_not_agree():
    assert agrees_with(a_statement(gross=999), [a_slip()]) is False


def test_the_share_taken_home_is_reported_in_basis_points():
    assert take_home_share(a_statement(gross=100000, net=80000)) == 8000


def test_a_year_of_nothing_takes_home_no_share():
    assert take_home_share(a_statement(gross=0, net=0)) == 0


def test_a_statement_is_drawn_from_the_payslips_behind_it():
    row = service().draw(MANAGER, DrawStatement(
        employee_id="ee-1", year_starts_on="2025-04-06", year_ends_on="2026-04-05"))
    assert row.gross == 543299 and row.net == 470255


def test_a_statement_starts_out_unissued():
    row = service().draw(MANAGER, DrawStatement(
        employee_id="ee-1", year_starts_on="2025-04-06", year_ends_on="2026-04-05"))
    assert row.issued_on is None


def test_a_year_with_no_payslips_draws_a_statement_of_nothing():
    row = service().draw(MANAGER, DrawStatement(
        employee_id="ee-2", year_starts_on="2025-04-06", year_ends_on="2026-04-05"))
    assert row.gross == 0


def test_a_second_statement_for_one_year_is_refused():
    svc = service()
    svc.draw(MANAGER, DrawStatement(
        employee_id="ee-1", year_starts_on="2025-04-06", year_ends_on="2026-04-05"))
    with pytest.raises(Conflict, match="already has a statement for that year"):
        svc.draw(MANAGER, DrawStatement(
            employee_id="ee-1", year_starts_on="2025-04-06",
            year_ends_on="2026-04-05"))


def test_a_statement_is_issued():
    svc = service()
    row = svc.draw(MANAGER, DrawStatement(
        employee_id="ee-1", year_starts_on="2025-04-06", year_ends_on="2026-04-05"))
    assert svc.issue(MANAGER, row.id, IssueStatement(
        issued_on="2026-05-31")).issued_on == "2026-05-31"


def test_a_statement_cannot_be_issued_twice():
    svc = service()
    row = svc.draw(MANAGER, DrawStatement(
        employee_id="ee-1", year_starts_on="2025-04-06", year_ends_on="2026-04-05"))
    svc.issue(MANAGER, row.id, IssueStatement(issued_on="2026-05-31"))
    with pytest.raises(Conflict, match="already been issued"):
        svc.issue(MANAGER, row.id, IssueStatement(issued_on="2026-06-30"))


def test_a_statement_nobody_drew_is_missing():
    with pytest.raises(NotFound, match="statement ys-9 was not found"):
        service().get(BUREAU, "ys-9")


def test_a_freshly_drawn_statement_agrees_with_its_payslips():
    svc = service()
    row = svc.draw(MANAGER, DrawStatement(
        employee_id="ee-1", year_starts_on="2025-04-06", year_ends_on="2026-04-05"))
    assert svc.agrees(MANAGER, row.id) is True


def test_statements_are_listed():
    svc = service()
    svc.draw(MANAGER, DrawStatement(
        employee_id="ee-1", year_starts_on="2025-04-06", year_ends_on="2026-04-05"))
    assert svc.list(MANAGER, ListStatements())["total"] == 1


def client():
    return build_client(a_store())


def test_the_route_draws_a_statement_and_answers_201():
    answer = client().post("/statements", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "year_starts_on": "2025-04-06",
        "year_ends_on": "2026-04-05"})
    assert answer.status_code == 201 and answer.json()["gross"] == 543299


def test_the_route_issues_a_statement():
    cl = client()
    row = cl.post("/statements", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "year_starts_on": "2025-04-06",
        "year_ends_on": "2026-04-05"}).json()
    answer = cl.post(f"/statements/{row['id']}/issue", headers=headers(MANAGER),
                     json={"issued_on": "2026-05-31"})
    assert answer.json()["issued_on"] == "2026-05-31"


def test_the_route_says_whether_a_statement_agrees():
    cl = client()
    row = cl.post("/statements", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "year_starts_on": "2025-04-06",
        "year_ends_on": "2026-04-05"}).json()
    assert cl.get(f"/statements/{row['id']}/agrees",
                  headers=headers(MANAGER)).json()["agrees"] is True


def test_the_route_answers_404_for_a_statement_nobody_drew():
    assert client().get("/statements/ys-9", headers=headers(BUREAU)).status_code == 404
