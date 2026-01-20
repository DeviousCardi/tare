"""Deduction instructions, and working them through a figure of pay."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_deductions, seed_elements,
    seed_employees, seed_employers, seed_suspensions,
)
from tare.common.types import DeductionInstruction
from tare.modules.deductions.rules import (
    asked_for, by_priority, due_in, take_from, total_short, total_taken,
)
from tare.modules.deductions.schemas import (
    InstructDeduction, ListDeductions, StopDeduction,
)
from tare.modules.deductions.service import DeductionsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_elements(store)
    seed_deductions(store)
    seed_suspensions(store)
    return store


def service():
    return DeductionsService(a_store())


def an_instruction(**kw) -> DeductionInstruction:
    base = dict(id="dd-9", employee_id="ee-1", employer_id="em-1", element_id="el-4",
                basis="fixed", amount=1500, priority=50, from_period=1,
                to_period=None, year_starts_on="2025-04-06")
    return DeductionInstruction(**{**base, **kw})


def test_instructions_run_in_priority_order():
    rows = by_priority([an_instruction(id="b", priority=60),
                        an_instruction(id="a", priority=10)])
    assert [row.id for row in rows] == ["a", "b"]


def test_instructions_of_one_priority_fall_back_to_the_earliest():
    rows = by_priority([an_instruction(id="b"), an_instruction(id="a")])
    assert [row.id for row in rows] == ["a", "b"]


def test_an_instruction_runs_in_the_period_it_starts():
    assert due_in(an_instruction(from_period=3), 3, "2025-04-06") is True


def test_an_instruction_does_not_run_before_it_starts():
    assert due_in(an_instruction(from_period=3), 2, "2025-04-06") is False


def test_an_open_instruction_runs_to_the_end_of_the_year():
    assert due_in(an_instruction(from_period=1), 12, "2025-04-06") is True


def test_a_stopped_instruction_still_runs_in_the_period_it_stopped():
    assert due_in(an_instruction(from_period=1, to_period=6), 6, "2025-04-06") is True


def test_a_stopped_instruction_does_not_run_after():
    assert due_in(an_instruction(from_period=1, to_period=6), 7, "2025-04-06") is False


def test_an_instruction_for_another_year_runs_in_none_of_this_one():
    assert due_in(an_instruction(), 3, "2024-04-06") is False


def test_a_fixed_instruction_asks_for_its_own_amount():
    assert asked_for(an_instruction(amount=1500), 200000) == 1500


def test_a_share_instruction_asks_for_its_rate_of_the_pay():
    assert asked_for(an_instruction(basis="share", amount=100), 200000) == 2000


def test_an_instruction_asks_for_nothing_out_of_no_pay():
    assert asked_for(an_instruction(), 0) == 0


def test_each_instruction_takes_what_it_asks_when_the_pay_stretches():
    rows = [an_instruction(id="a", amount=1500), an_instruction(id="b", amount=2500)]
    assert [row.taken for row in take_from(rows, 200000)] == [1500, 2500]


def test_the_higher_priority_is_taken_first_when_the_pay_runs_out():
    rows = [an_instruction(id="a", amount=1500, priority=10),
            an_instruction(id="b", amount=2500, priority=20)]
    taken = take_from(rows, 2000)
    assert [row.taken for row in taken] == [1500, 500]


def test_what_could_not_be_taken_is_recorded_rather_than_forgotten():
    rows = [an_instruction(id="a", amount=1500, priority=10),
            an_instruction(id="b", amount=2500, priority=20)]
    assert total_short(take_from(rows, 2000)) == 2000


def test_nothing_is_taken_once_the_pay_is_gone():
    rows = [an_instruction(id="a", amount=5000, priority=10),
            an_instruction(id="b", amount=2500, priority=20)]
    assert take_from(rows, 3000)[1].taken == 0


def test_an_element_held_off_is_skipped_entirely():
    rows = [an_instruction(id="a", element_id="el-4")]
    assert take_from(rows, 200000, ["el-4"]) == []


def test_no_instructions_take_nothing():
    assert total_taken(take_from([], 200000)) == 0


def test_no_pay_means_nothing_is_taken():
    assert total_taken(take_from([an_instruction()], 0)) == 0


def test_the_bureau_lists_every_instruction():
    assert service().list(BUREAU, ListDeductions())["total"] == 2


def test_a_listing_can_be_narrowed_to_one_person():
    assert service().list(MANAGER, ListDeductions(employee_id="ee-1"))["total"] == 1


def test_a_listing_can_be_narrowed_to_a_period():
    answer = service().list(MANAGER, ListDeductions(
        due_in_period=9, year_starts_on="2025-04-06"))
    assert answer["total"] == 1


def test_an_instruction_can_be_read():
    assert service().get(MANAGER, "dd-1").amount == 1500


def test_an_instruction_nobody_made_is_missing():
    with pytest.raises(NotFound, match="deduction instruction dd-9 was not found"):
        service().get(BUREAU, "dd-9")


def test_an_instruction_is_made():
    row = service().instruct(MANAGER, InstructDeduction(
        employee_id="ee-3", element_id="el-4", basis="fixed", amount=900,
        from_period=1, year_starts_on="2025-04-06"))
    assert row.priority == 50


def test_only_a_deduction_element_can_be_instructed():
    with pytest.raises(Refused, match="only a deduction element"):
        service().instruct(MANAGER, InstructDeduction(
            employee_id="ee-3", element_id="el-1", basis="fixed", amount=900,
            from_period=1, year_starts_on="2025-04-06"))


def test_a_share_of_more_than_the_whole_is_refused():
    with pytest.raises(Refused, match="cannot be more than the whole"):
        service().instruct(MANAGER, InstructDeduction(
            employee_id="ee-3", element_id="el-4", basis="share", amount=10001,
            from_period=1, year_starts_on="2025-04-06"))


def test_an_instruction_cannot_stop_before_it_starts():
    with pytest.raises(Refused, match="cannot stop before it starts"):
        service().instruct(MANAGER, InstructDeduction(
            employee_id="ee-3", element_id="el-4", basis="fixed", amount=900,
            from_period=6, to_period=3, year_starts_on="2025-04-06"))


def test_a_second_instruction_over_one_already_running_is_refused():
    with pytest.raises(Conflict, match="already instructed for period"):
        service().instruct(MANAGER, InstructDeduction(
            employee_id="ee-1", element_id="el-4", basis="fixed", amount=900,
            from_period=5, year_starts_on="2025-04-06"))


def test_an_instruction_is_stopped():
    assert service().stop(MANAGER, "dd-1", StopDeduction(to_period=8)).to_period == 8


def test_an_instruction_cannot_be_stopped_twice():
    with pytest.raises(Conflict, match="already been stopped"):
        service().stop(MANAGER, "dd-2", StopDeduction(to_period=8))


def test_a_run_takes_what_the_instructions_ask_for():
    answer = service().run(MANAGER, "ee-1", 1, "2025-04-06", 200000)
    assert answer["total_taken"] == 1500 and answer["total_short"] == 0


def test_a_run_skips_an_element_that_is_suspended():
    # ee-1's union subscription is suspended from period 3.
    answer = service().run(MANAGER, "ee-1", 3, "2025-04-06", 200000)
    assert answer["lines"] == [] and answer["total_taken"] == 0


def test_a_run_against_no_pay_takes_nothing_and_records_what_it_could_not():
    answer = service().run(MANAGER, "ee-1", 1, "2025-04-06", 0)
    assert answer["total_taken"] == 0


def client():
    return build_client(a_store())


def test_the_route_lists_instructions():
    assert client().get("/deductions", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_runs_the_deductions():
    answer = client().get(
        "/deductions/run/ee-1?period=1&year_starts_on=2025-04-06&pay=200000",
        headers=headers(MANAGER))
    assert answer.json()["total_taken"] == 1500


def test_the_route_makes_an_instruction_and_answers_201():
    answer = client().post("/deductions", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "element_id": "el-4", "basis": "fixed",
        "amount": 900, "from_period": 1, "year_starts_on": "2025-04-06"})
    assert answer.status_code == 201


def test_the_route_stops_an_instruction():
    answer = client().post("/deductions/dd-1/stop", headers=headers(MANAGER),
                           json={"to_period": 8})
    assert answer.json()["to_period"] == 8
