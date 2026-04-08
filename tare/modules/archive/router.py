"""Routes for the archive."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.archive.schemas import (
    ArchiveOut, ArchiveTotalsOut, CloseOffRun, ListArchive,
)
from tare.modules.archive.service import ArchiveService

router = APIRouter(prefix="/archive", tags=["archive"])


@router.get("")
def list_archive(
    operator: TheOperator, store: TheStore,
    employer_id: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = ArchiveService(store).list(operator, ListArchive(
        employer_id=employer_id, start=start, end=end, limit=limit, offset=offset))
    return {"data": [ArchiveOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/totals")
def archive_totals(operator: TheOperator, store: TheStore) -> ArchiveTotalsOut:
    return ArchiveTotalsOut(**ArchiveService(store).totals(operator))


@router.get("/holds/{run_id}")
def archive_holds(run_id: str, operator: TheOperator, store: TheStore) -> dict:
    return {"run_id": run_id, "closed_off": ArchiveService(store).holds(operator, run_id)}


@router.get("/{entry_id}")
def get_entry(entry_id: str, operator: TheOperator, store: TheStore) -> ArchiveOut:
    return ArchiveOut.of(ArchiveService(store).get(operator, entry_id))


@router.post("", status_code=201)
def close_off_run(dto: CloseOffRun, operator: TheOperator, store: TheStore) -> ArchiveOut:
    return ArchiveOut.of(ArchiveService(store).close_off(operator, dto))
