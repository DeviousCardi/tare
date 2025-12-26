"""Routes for absences."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.absences.schemas import (
    AbsenceOut, AmendAbsence, ListAbsences, RecordAbsence, SpellOut,
)
from tare.modules.absences.service import AbsencesService

router = APIRouter(prefix="/absences", tags=["absences"])


@router.get("")
def list_absences(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    kind: str | None = Query(default=None),
    covering: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = AbsencesService(store).list(operator, ListAbsences(
        employee_id=employee_id, kind=kind, covering=covering,
        limit=limit, offset=offset))
    return {"data": [AbsenceOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/days/{employee_id}")
def absence_days(
    employee_id: str, start: str, end: str, operator: TheOperator, store: TheStore,
    kind: str | None = Query(default=None),
) -> dict:
    return {"employee_id": employee_id, "start": start, "end": end, "kind": kind,
            "days": AbsencesService(store).days(operator, employee_id, start, end, kind)}


@router.get("/{absence_id}")
def get_absence(absence_id: str, operator: TheOperator, store: TheStore) -> AbsenceOut:
    return AbsenceOut.of(AbsencesService(store).get(operator, absence_id))


@router.get("/{absence_id}/spell")
def absence_spell(absence_id: str, operator: TheOperator, store: TheStore) -> SpellOut:
    return SpellOut(**AbsencesService(store).spell(operator, absence_id))


@router.post("", status_code=201)
def record_absence(dto: RecordAbsence, operator: TheOperator, store: TheStore) -> AbsenceOut:
    return AbsenceOut.of(AbsencesService(store).record(operator, dto))


@router.post("/{absence_id}/amend")
def amend_absence(
    absence_id: str, dto: AmendAbsence, operator: TheOperator, store: TheStore,
) -> AbsenceOut:
    return AbsenceOut.of(AbsencesService(store).amend(operator, absence_id, dto))
