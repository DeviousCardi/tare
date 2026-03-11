"""Routes for pension schemes."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.pensions.schemas import (
    CloseScheme, ListSchemes, OpenScheme, SchemeOut, SharesOut,
)
from tare.modules.pensions.service import PensionsService

router = APIRouter(prefix="/pensions", tags=["pensions"])


@router.get("")
def list_schemes(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    open_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = PensionsService(store).list(operator, ListSchemes(
        employer_id=employer_id, open_on=open_on, limit=limit, offset=offset))
    return {"data": [SchemeOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{scheme_id}")
def get_scheme(scheme_id: str, operator: TheOperator, store: TheStore) -> SchemeOut:
    return SchemeOut.of(PensionsService(store).get(operator, scheme_id))


@router.get("/{scheme_id}/shares")
def scheme_shares(
    scheme_id: str, pensionable: int, operator: TheOperator, store: TheStore,
) -> SharesOut:
    return SharesOut(**PensionsService(store).shares(operator, scheme_id, pensionable))


@router.post("", status_code=201)
def open_scheme(dto: OpenScheme, operator: TheOperator, store: TheStore) -> SchemeOut:
    return SchemeOut.of(PensionsService(store).open(operator, dto))


@router.post("/{scheme_id}/close")
def close_scheme(
    scheme_id: str, dto: CloseScheme, operator: TheOperator, store: TheStore,
) -> SchemeOut:
    return SchemeOut.of(PensionsService(store).close(operator, scheme_id, dto))
