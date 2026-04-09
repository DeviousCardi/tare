"""Routes for journals."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.journals.schemas import (
    JournalLineOut, JournalOut, ListJournal, PostRun,
)
from tare.modules.journals.service import JournalsService

router = APIRouter(prefix="/journals", tags=["journals"])


def _as_out(answer: dict) -> JournalOut:
    return JournalOut(
        run_id=answer["run_id"],
        lines=[JournalLineOut.of(row) for row in answer["lines"]],
        debits=answer["debits"], credits=answer["credits"],
        balances=answer["balances"])


@router.get("")
def list_journal(
    operator: TheOperator, store: TheStore,
    run_id: str | None = Query(default=None),
    account: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = JournalsService(store).list(operator, ListJournal(
        run_id=run_id, account=account, limit=limit, offset=offset))
    return {"data": [JournalLineOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{run_id}")
def journal_of(run_id: str, operator: TheOperator, store: TheStore) -> JournalOut:
    return _as_out(JournalsService(store).of(operator, run_id))


@router.post("", status_code=201)
def post_run(dto: PostRun, operator: TheOperator, store: TheStore) -> JournalOut:
    return _as_out(JournalsService(store).post(operator, dto))
