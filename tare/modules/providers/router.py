"""Routes for providers."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.providers.schemas import (
    ChangeAccount, ListProviders, ProviderOut, RegisterProvider,
)
from tare.modules.providers.service import ProvidersService

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def list_providers(
    operator: TheOperator, store: TheStore,
    kind: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ProvidersService(store).list(operator, ListProviders(
        kind=kind, limit=limit, offset=offset))
    return {"data": [ProviderOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/{provider_id}")
def get_provider(provider_id: str, operator: TheOperator, store: TheStore) -> ProviderOut:
    return ProviderOut.of(ProvidersService(store).get(operator, provider_id))


@router.post("", status_code=201)
def register_provider(
    dto: RegisterProvider, operator: TheOperator, store: TheStore,
) -> ProviderOut:
    return ProviderOut.of(ProvidersService(store).register(operator, dto))


@router.post("/{provider_id}/account")
def change_account(
    provider_id: str, dto: ChangeAccount, operator: TheOperator, store: TheStore,
) -> ProviderOut:
    return ProviderOut.of(ProvidersService(store).change_account(
        operator, provider_id, dto))
