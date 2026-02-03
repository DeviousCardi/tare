"""Routes for payroll runs."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.runs.schemas import CommitRun, ListRuns, OpenRun, RunOut, RunTotalsOut
from tare.modules.runs.service import RunsService

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    calendar_id: str | None = Query(default=None),
    period: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = RunsService(store).list(operator, ListRuns(
        employer_id=employer_id, calendar_id=calendar_id, period=period,
        status=status, limit=limit, offset=offset))
    return {"data": [RunOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{run_id}")
def get_run(run_id: str, operator: TheOperator, store: TheStore) -> RunOut:
    return RunOut.of(RunsService(store).get(operator, run_id))


@router.get("/{run_id}/totals")
def run_totals(run_id: str, operator: TheOperator, store: TheStore) -> RunTotalsOut:
    return RunTotalsOut(**RunsService(store).totals(operator, run_id))


@router.post("", status_code=201)
def open_run(dto: OpenRun, operator: TheOperator, store: TheStore) -> RunOut:
    return RunOut.of(RunsService(store).open(operator, dto))


@router.post("/{run_id}/commit")
def commit_run(
    run_id: str, dto: CommitRun, operator: TheOperator, store: TheStore,
) -> RunOut:
    return RunOut.of(RunsService(store).commit(operator, run_id, dto))


@router.post("/{run_id}/abandon")
def abandon_run(run_id: str, operator: TheOperator, store: TheStore) -> RunOut:
    return RunOut.of(RunsService(store).abandon(operator, run_id))
