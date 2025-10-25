"""Routes for the terms people are employed on."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.contracts.schemas import (
    ChangeTerms, ContractOut, EndContract, ListContracts, OpenContract, TermsOut,
)
from tare.modules.contracts.service import ContractsService

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("")
def list_contracts(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    employer_id: str | None = Query(default=None),
    in_force_on: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ContractsService(store).list(operator, ListContracts(
        employee_id=employee_id, employer_id=employer_id, in_force_on=in_force_on,
        limit=limit, offset=offset))
    return {"data": [ContractOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{contract_id}")
def get_contract(contract_id: str, operator: TheOperator, store: TheStore) -> ContractOut:
    return ContractOut.of(ContractsService(store).get(operator, contract_id))


@router.get("/{contract_id}/terms")
def contract_terms(
    contract_id: str, upto: str, operator: TheOperator, store: TheStore,
) -> TermsOut:
    return TermsOut(**ContractsService(store).terms(operator, contract_id, upto))


@router.post("", status_code=201)
def open_contract(dto: OpenContract, operator: TheOperator, store: TheStore) -> ContractOut:
    return ContractOut.of(ContractsService(store).open(operator, dto))


@router.post("/{contract_id}/end")
def end_contract(
    contract_id: str, dto: EndContract, operator: TheOperator, store: TheStore,
) -> ContractOut:
    return ContractOut.of(ContractsService(store).end(operator, contract_id, dto))


@router.post("/of/{employee_id}/terms")
def change_terms(
    employee_id: str, dto: ChangeTerms, operator: TheOperator, store: TheStore,
) -> ContractOut:
    return ContractOut.of(ContractsService(store).change_terms(operator, employee_id, dto))
