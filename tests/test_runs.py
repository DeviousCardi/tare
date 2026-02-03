"""Payroll runs: one pass of the payroll over an employer's period."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_bands, seed_calendars,
    seed_contracts, seed_deductions, seed_elements, seed_employees, seed_employers,
    seed_levy_codes, seed_rates, seed_timesheets,
)
from tare.common.types import Payslip, PayrollRun
from tare.modules.runs.rules import (
    gross_total, headcount, is_committed, is_open, revenue_total, run_total,
    sort_by_period,
)
from tare.modules.runs.schemas import CommitRun, ListRuns, OpenRun
from tare.modules.runs.service import RunsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_contracts, seed_elements,
                 seed_rates, seed_calendars, seed_timesheets, seed_levy_codes,
                 seed_bands, seed_deductions):
        seed(store)
    return store


def service():
    return RunsService(a_store())


def opened(svc, period: int = 2):
    return svc.open(MANAGER, OpenRun(
        employer_id="em-1", calendar_id="pc-1", period=period, opened_on="2025-06-06"))


def a_run(**kw) -> PayrollRun:
    base = dict(id="rn-9", employer_id="em-1", calendar_id="pc-1", period=1,
                status="draft", opened_on="2025-05-06", committed_on=None)
    return PayrollRun(**{**base, **kw})


def a_slip(**kw) -> Payslip:
    base = dict(id="ps-slip-9", run_id="rn-9", employee_id="ee-1", employer_id="em-1",
                period=1, start="2025-04-06", end="2025-05-05", gross=268000,
                taxable=268000, free_pay=108000, levy=32000, contributory=268000,
                contributions=12800, deductions=1500, net=221700)
    return Payslip(**{**base, **kw})


def test_runs_read_earliest_period_first():
    rows = sort_by_period([a_run(period=2), a_run(period=1)])
    assert [row.period for row in rows] == [1, 2]


def test_a_fresh_run_is_open():
    assert is_open(a_run(status="draft")) is True


def test_a_committed_run_is_no_longer_open():
    assert is_open(a_run(status="committed")) is False


def test_a_committed_run_reads_as_committed():
    assert is_committed(a_run(status="committed")) is True


# Every payslip below carries a net figure of its own above nothing, which is
# what an ordinary run produces, so the totals do not depend on how a payslip
# carrying a figure below nothing is read.
def test_a_run_comes_to_the_net_figures_on_its_payslips():
    assert run_total([a_slip(net=221700), a_slip(id="b", net=248555)]) == 470255


def test_a_run_with_no_payslips_comes_to_nothing():
    assert run_total([]) == 0


def test_a_run_adds_the_gross_figures_up_too():
    assert gross_total([a_slip(gross=268000), a_slip(id="b", gross=275299)]) == 543299


def test_what_a_run_owes_the_revenue_takes_in_the_levy_and_contributions():
    assert revenue_total([a_slip(levy=32000, contributions=12800)]) == 44800


def test_a_run_counts_each_person_once():
    assert headcount([a_slip(employee_id="ee-1"), a_slip(id="b", employee_id="ee-1")]) == 1


def test_a_run_counts_two_people_as_two():
    assert headcount([a_slip(employee_id="ee-1"), a_slip(id="b", employee_id="ee-2")]) == 2


def test_a_run_is_opened_as_a_draft():
    assert opened(service()).status == "draft"


def test_a_second_run_over_a_period_already_run_is_refused():
    svc = service()
    opened(svc)
    with pytest.raises(Conflict, match="has already been run"):
        opened(svc)


def test_a_run_on_another_employers_calendar_is_refused():
    with pytest.raises(Refused, match="belongs to another employer"):
        service().open(BUREAU, OpenRun(
            employer_id="em-1", calendar_id="pc-3", period=2, opened_on="2025-06-06"))


def test_a_period_outside_the_year_is_refused():
    with pytest.raises(Refused, match="is not in a year of"):
        service().open(MANAGER, OpenRun(
            employer_id="em-1", calendar_id="pc-1", period=13, opened_on="2025-06-06"))


def test_a_manager_cannot_open_a_run_at_another_employer():
    with pytest.raises(Refused):
        service().open(MANAGER, OpenRun(
            employer_id="em-2", calendar_id="pc-3", period=2, opened_on="2025-06-06"))


def test_committing_a_run_writes_a_payslip():
    svc = service()
    run = opened(svc)
    svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-06-07"))
    assert svc.totals(MANAGER, run.id)["headcount"] == 1


def test_a_committed_run_carries_the_day_it_was_committed():
    svc = service()
    run = opened(svc)
    assert svc.commit(MANAGER, run.id, CommitRun(
        committed_on="2025-06-07")).committed_on == "2025-06-07"


def test_a_committed_run_totals_what_it_paid():
    svc = service()
    run = opened(svc)
    svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-06-07"))
    totals = svc.totals(MANAGER, run.id)
    assert totals["gross"] == 275299 and totals["net"] == 248555


def test_a_committed_run_totals_what_it_owes_the_revenue():
    svc = service()
    run = opened(svc)
    svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-06-07"))
    assert svc.totals(MANAGER, run.id)["revenue"] == 25244


def test_committing_writes_the_lines_behind_each_payslip():
    store = a_store()
    svc = RunsService(store)
    run = opened(svc)
    svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-06-07"))
    assert len(store.payslip_lines.all()) == 3


def test_a_run_passes_over_somebody_with_nothing_to_be_paid():
    # ee-3's contract ended before the period, so no payslip is written and the
    # run still commits for everybody else.
    svc = service()
    run = opened(svc)
    svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-06-07"))
    assert svc.totals(MANAGER, run.id)["headcount"] == 1


def test_a_run_cannot_be_committed_twice():
    svc = service()
    run = opened(svc)
    svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-06-07"))
    with pytest.raises(Conflict, match="was already committed"):
        svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-06-08"))


def test_a_run_cannot_commit_before_it_was_opened():
    svc = service()
    run = opened(svc)
    with pytest.raises(Refused, match="cannot commit before it was opened"):
        svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-01-01"))


def test_a_run_is_abandoned():
    svc = service()
    assert svc.abandon(MANAGER, opened(svc).id).status == "abandoned"


def test_an_abandoned_period_can_be_run_again():
    svc = service()
    svc.abandon(MANAGER, opened(svc).id)
    assert opened(svc).status == "draft"


def test_a_committed_run_cannot_be_abandoned():
    svc = service()
    run = opened(svc)
    svc.commit(MANAGER, run.id, CommitRun(committed_on="2025-06-07"))
    with pytest.raises(Conflict, match="was already committed"):
        svc.abandon(MANAGER, run.id)


def test_a_run_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="run rn-99 was not found"):
        service().get(BUREAU, "rn-99")


def test_runs_are_listed():
    svc = service()
    opened(svc)
    assert svc.list(MANAGER, ListRuns())["total"] == 1


def test_a_listing_can_be_narrowed_to_what_is_still_a_draft():
    svc = service()
    opened(svc)
    assert svc.list(MANAGER, ListRuns(status="draft"))["total"] == 1


def client():
    return build_client(a_store())


def test_the_route_opens_a_run_and_answers_201():
    answer = client().post("/runs", headers=headers(MANAGER), json={
        "employer_id": "em-1", "calendar_id": "pc-1", "period": 2,
        "opened_on": "2025-06-06"})
    assert answer.status_code == 201


def test_the_route_commits_a_run_and_totals_it():
    cl = client()
    run = cl.post("/runs", headers=headers(MANAGER), json={
        "employer_id": "em-1", "calendar_id": "pc-1", "period": 2,
        "opened_on": "2025-06-06"}).json()
    cl.post(f"/runs/{run['id']}/commit", headers=headers(MANAGER),
            json={"committed_on": "2025-06-07"})
    assert cl.get(f"/runs/{run['id']}/totals", headers=headers(MANAGER)).json()["net"] == 248555


def test_the_route_answers_409_for_a_period_already_run():
    cl = client()
    body = {"employer_id": "em-1", "calendar_id": "pc-1", "period": 2,
            "opened_on": "2025-06-06"}
    cl.post("/runs", headers=headers(MANAGER), json=body)
    assert cl.post("/runs", headers=headers(MANAGER), json=body).status_code == 409


def test_the_route_answers_404_for_a_run_nobody_opened():
    assert client().get("/runs/rn-99", headers=headers(BUREAU)).status_code == 404
