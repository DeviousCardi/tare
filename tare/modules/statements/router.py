"""Routes for year-end statements."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.statements.schemas import (
    DrawStatement, IssueStatement, ListStatements, StatementOut,
)
from tare.modules.statements.service import StatementsService

router = APIRouter(prefix="/statements", tags=["statements"])


@router.get("")
def list_statements(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    year_starts_on: str | None = Query(default=None),
    issued_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = StatementsService(store).list(operator, ListStatements(
        employee_id=employee_id, year_starts_on=year_starts_on,
        issued_only=issued_only, limit=limit, offset=offset))
    return {"data": [StatementOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{statement_id}")
def get_statement(
    statement_id: str, operator: TheOperator, store: TheStore,
) -> StatementOut:
    return StatementOut.of(StatementsService(store).get(operator, statement_id))


@router.get("/{statement_id}/agrees")
def statement_agrees(
    statement_id: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"statement_id": statement_id,
            "agrees": StatementsService(store).agrees(operator, statement_id)}


@router.post("", status_code=201)
def draw_statement(
    dto: DrawStatement, operator: TheOperator, store: TheStore,
) -> StatementOut:
    return StatementOut.of(StatementsService(store).draw(operator, dto))


@router.post("/{statement_id}/issue")
def issue_statement(
    statement_id: str, dto: IssueStatement, operator: TheOperator, store: TheStore,
) -> StatementOut:
    return StatementOut.of(StatementsService(store).issue(operator, statement_id, dto))
