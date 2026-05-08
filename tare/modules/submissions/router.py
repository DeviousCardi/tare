"""Routes for submissions."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.submissions.schemas import (
    FilingStandingOut, ListSubmissions, SendSubmission, SubmissionOut,
)
from tare.modules.submissions.service import SubmissionsService

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("")
def list_submissions(
    operator: TheOperator, store: TheStore,
    filing_id: str | None = Query(default=None),
    accepted_only: bool = Query(default=False),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = SubmissionsService(store).list(operator, ListSubmissions(
        filing_id=filing_id, accepted_only=accepted_only, limit=limit, offset=offset))
    return {"data": [SubmissionOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/standing/{filing_id}")
def filing_standing(
    filing_id: str, operator: TheOperator, store: TheStore,
) -> FilingStandingOut:
    return FilingStandingOut(**SubmissionsService(store).standing(operator, filing_id))


@router.get("/{submission_id}")
def get_submission(
    submission_id: str, operator: TheOperator, store: TheStore,
) -> SubmissionOut:
    return SubmissionOut.of(SubmissionsService(store).get(operator, submission_id))


@router.post("", status_code=201)
def send_submission(
    dto: SendSubmission, operator: TheOperator, store: TheStore,
) -> SubmissionOut:
    return SubmissionOut.of(SubmissionsService(store).send(operator, dto))
