"""Routes for the registry."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.registry.schemas import ShelfOut, ShelfRowsOut
from tare.modules.registry.service import RegistryService

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("")
def list_shelves(operator: TheOperator, store: TheStore) -> dict:
    rows = RegistryService(store).shelves(operator)
    return {"data": [ShelfOut(**row) for row in rows], "total": len(rows)}


@router.get("/{name}")
def shelf_rows(
    name: str, operator: TheOperator, store: TheStore,
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> ShelfRowsOut:
    return ShelfRowsOut(**RegistryService(store).rows(operator, name, limit, offset))


@router.get("/{name}/count")
def shelf_count(name: str, operator: TheOperator, store: TheStore) -> dict:
    return {"name": name, "rows": RegistryService(store).count(operator, name)}
