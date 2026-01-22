"""Gross pay: what somebody earned in a period, before anything comes off."""

import pytest

from tare.common.errors import NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_calendars, seed_contracts,
    seed_elements, seed_employees, seed_employers, seed_rates, seed_timesheets,
)
from tare.common.types import PayRate
from tare.modules.elements.rules import Entry
from tare.modules.gross.rules import Piece, combine, entries_for, periodic, piece_amount
from tare.modules.gross.service import GrossService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_contracts, seed_elements,
                 seed_rates, seed_calendars, seed_timesheets):
        seed(store)
    return store


def service():
    return GrossService(a_store())


def a_rate(**kw) -> PayRate:
    base = dict(id="rt-9", employee_id="ee-1", employer_id="em-1", element_id="el-1",
                basis="fixed", amount=100000, effective_from="2024-04-06")
    return PayRate(**{**base, **kw})


def test_a_year_divides_into_twelve_monthly_periods():
    assert periodic(1200000, "monthly") == 100000


def test_a_year_divides_into_fifty_two_weekly_periods():
    assert periodic(5200000, "weekly") == 100000


def test_a_period_of_a_year_rounds_half_up():
    # 1000 over 12 is 83.33, which rounds to 83.
    assert periodic(1000, "monthly") == 83


def test_a_fixed_piece_ignores_the_hours_behind_it():
    piece = Piece(element_id="el-1", hours=40, rate=a_rate(basis="fixed", amount=100000))
    assert piece_amount(piece, 1000) == 100000


def test_an_hourly_piece_pays_for_the_hours_behind_it():
    piece = Piece(element_id="el-2", hours=4, rate=a_rate(basis="hourly", amount=1500))
    assert piece_amount(piece, 0) == 6000


def test_a_multiple_piece_pays_a_share_of_the_contracts_hourly_rate():
    piece = Piece(element_id="el-2", hours=4, rate=a_rate(basis="multiple", amount=15000))
    assert piece_amount(piece, 1000) == 6000


def test_entries_read_in_element_order():
    pieces = [Piece("el-2", 0, a_rate(basis="fixed", amount=1)),
              Piece("el-1", 0, a_rate(basis="fixed", amount=2))]
    assert [entry.element_id for entry in entries_for(pieces, 0)] == ["el-1", "el-2"]


def test_two_pieces_against_one_element_fold_into_one_line():
    folded = combine([Entry("el-1", 1000), Entry("el-1", 500)])
    assert folded == [Entry("el-1", 1500)]


def test_pieces_against_different_elements_stay_apart():
    folded = combine([Entry("el-2", 500), Entry("el-1", 1000)])
    assert [entry.element_id for entry in folded] == ["el-1", "el-2"]


def test_nothing_folds_to_nothing():
    assert combine([]) == []


def test_a_period_with_no_hours_pays_the_fixed_rate_alone():
    answer = service().of(MANAGER, "ee-1", "pc-1", 3)
    assert answer["gross"] == 268000 and len(answer["lines"]) == 1


def test_a_period_with_approved_hours_pays_for_them_too():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert answer["gross"] == 275299


def test_the_overtime_line_carries_the_hours_behind_it():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    overtime = [line for line in answer["lines"] if line["code"] == "OT"][0]
    assert overtime["hours"] == 3 and overtime["amount"] == 7299


def test_the_lines_name_the_elements_they_are_for():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert [line["code"] for line in answer["lines"]] == ["BASIC", "OT"]


def test_the_taxable_figure_takes_in_every_taxable_payment():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert answer["taxable"] == 275299


def test_overtime_is_not_pensionable_so_the_pensionable_figure_is_lower():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert answer["pensionable"] == 268000


def test_the_period_reports_the_window_it_covers():
    answer = service().of(MANAGER, "ee-1", "pc-1", 2)
    assert answer["start"] == "2025-05-06" and answer["end"] == "2025-06-05"


def test_a_run_reads_the_rate_in_force_at_the_end_of_the_period():
    # The basic rate went up on 2025-04-06, so a period ending after that
    # reads the raised figure rather than the older one.
    assert service().of(MANAGER, "ee-1", "pc-1", 1)["gross"] == 268000


def test_a_calendar_belonging_to_another_employer_is_refused():
    with pytest.raises(Refused, match="belongs to another employer"):
        service().of(BUREAU, "ee-1", "pc-3", 2)


def test_a_period_outside_the_year_is_refused():
    with pytest.raises(Refused, match="is not in a year of"):
        service().of(MANAGER, "ee-1", "pc-1", 13)


def test_somebody_who_was_not_in_post_across_the_period_is_refused():
    with pytest.raises(Refused, match="was not in post across that period"):
        service().of(MANAGER, "ee-3", "pc-1", 8)


def test_a_manager_cannot_work_out_another_employers_gross():
    with pytest.raises(Refused):
        service().of(MANAGER, "ee-4", "pc-3", 2)


def test_somebody_nobody_has_is_missing():
    with pytest.raises(NotFound, match="employee ee-99 was not found"):
        service().of(BUREAU, "ee-99", "pc-1", 2)


def client():
    return build_client(a_store())


def test_the_route_reports_gross_pay():
    answer = client().get("/gross/ee-1?calendar_id=pc-1&period=2", headers=headers(MANAGER))
    assert answer.json()["gross"] == 275299


def test_the_route_reports_the_lines_behind_the_gross():
    answer = client().get("/gross/ee-1?calendar_id=pc-1&period=2", headers=headers(MANAGER))
    assert len(answer.json()["lines"]) == 2


def test_the_route_answers_400_for_a_period_outside_the_year():
    answer = client().get("/gross/ee-1?calendar_id=pc-1&period=13", headers=headers(MANAGER))
    assert answer.status_code == 400


def test_the_route_answers_404_for_somebody_nobody_has():
    answer = client().get("/gross/ee-99?calendar_id=pc-1&period=2", headers=headers(BUREAU))
    assert answer.status_code == 404
