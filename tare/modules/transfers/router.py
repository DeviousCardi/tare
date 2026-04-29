"""Routes for transfers."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.transfers.schemas import (
    AcceptTransfer, CarriesOut, ListTransfers, ProposeTransfer, TransferOut,
)
from tare.modules.transfers.service import TransfersService

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.get("")
def list_transfers(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    to_employer_id: str | None = Query(default=None),
    accepted_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = TransfersService(store).list(operator, ListTransfers(
        employee_id=employee_id, to_employer_id=to_employer_id,
        accepted_only=accepted_only, limit=limit, offset=offset))
    return {"data": [TransferOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/where/{employee_id}")
def where(employee_id: str, operator: TheOperator, store: TheStore) -> dict:
    return {"employee_id": employee_id,
            "employer_id": TransfersService(store).where(operator, employee_id)}


@router.get("/{transfer_id}")
def get_transfer(transfer_id: str, operator: TheOperator, store: TheStore) -> TransferOut:
    return TransferOut.of(TransfersService(store).get(operator, transfer_id))


@router.get("/{transfer_id}/carries")
def transfer_carries(
    transfer_id: str, operator: TheOperator, store: TheStore,
) -> CarriesOut:
    return CarriesOut(**TransfersService(store).carries(operator, transfer_id))


@router.post("", status_code=201)
def propose_transfer(
    dto: ProposeTransfer, operator: TheOperator, store: TheStore,
) -> TransferOut:
    return TransferOut.of(TransfersService(store).propose(operator, dto))


@router.post("/{transfer_id}/accept")
def accept_transfer(
    transfer_id: str, dto: AcceptTransfer, operator: TheOperator, store: TheStore,
) -> TransferOut:
    return TransferOut.of(TransfersService(store).accept(operator, transfer_id, dto))
