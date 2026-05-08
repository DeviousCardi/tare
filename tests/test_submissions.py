"""Submissions: what was sent to the Revenue, and what came back."""

import pytest

from tare.common.errors import NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_filings,
    seed_submissions,
)
from tare.common.types import PayrollRun, Submission
from tare.modules.submissions.rules import (
    attempts_on, for_filing, is_settled, latest_for, sort_by_sent,
)
from tare.modules.submissions.schemas import ListSubmissions, SendSubmission
from tare.modules.submissions.service import SubmissionsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_filings, seed_submissions):
        seed(store)
    for run_id, employer_id, period in (("rn-1", "em-1", 1), ("rn-2", "em-1", 2),
                                        ("rn-3", "em-2", 1)):
        store.runs.insert(PayrollRun(
            id=run_id, employer_id=employer_id, calendar_id="pc-1", period=period,
            status="committed", opened_on="2025-05-06", committed_on="2025-05-07"))
    return store


def service():
    return SubmissionsService(a_store())


def a_submission(**kw) -> Submission:
    base = dict(id="sb-9", filing_id="fl-1", employer_id="em-1",
                sent_on="2025-05-12", reference="RTI/2025/0009", accepted=True,
                note="")
    return Submission(**{**base, **kw})


def test_submissions_read_earliest_sent_first():
    rows = sort_by_sent([a_submission(id="b", sent_on="2025-05-14"),
                         a_submission(id="a", sent_on="2025-05-12")])
    assert [row.id for row in rows] == ["a", "b"]


def test_the_attempts_on_a_filing_are_found():
    assert [row.id for row in for_filing(a_store().submissions.all(), "fl-1")] == ["sb-1"]


def test_a_filing_nobody_sent_has_no_attempts():
    assert for_filing(a_store().submissions.all(), "fl-9") == []


# Every seeded filing was sent once and taken first time, which is the ordinary
# case, so what stands does not depend on how a filing sent again after a
# rejection is read.
def test_the_attempt_that_stands_is_the_one_that_was_sent():
    assert latest_for(a_store().submissions.all(), "fl-1").reference == "RTI/2025/0001"


def test_a_filing_nobody_sent_has_nothing_standing():
    assert latest_for(a_store().submissions.all(), "fl-9") is None


def test_a_filing_the_revenue_took_is_settled():
    assert is_settled(a_store().submissions.all(), "fl-1") is True


def test_a_filing_nobody_sent_is_not_settled():
    assert is_settled(a_store().submissions.all(), "fl-9") is False


def test_a_filing_the_revenue_turned_down_is_not_settled():
    rows = [a_submission(accepted=False)]
    assert is_settled(rows, "fl-1") is False


def test_the_attempts_on_a_filing_are_counted():
    assert attempts_on(a_store().submissions.all(), "fl-1") == 1


def test_a_filing_nobody_sent_has_no_attempts_counted():
    assert attempts_on(a_store().submissions.all(), "fl-9") == 0


def test_the_bureau_lists_every_submission():
    assert service().list(BUREAU, ListSubmissions())["total"] == 3


def test_a_manager_lists_only_their_own_employers_submissions():
    assert service().list(MANAGER, ListSubmissions())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_filing():
    assert service().list(MANAGER, ListSubmissions(filing_id="fl-1"))["total"] == 1


def test_a_submission_can_be_read():
    assert service().get(MANAGER, "sb-1").reference == "RTI/2025/0001"


def test_a_submission_nobody_sent_is_missing():
    with pytest.raises(NotFound, match="submission sb-9 was not found"):
        service().get(BUREAU, "sb-9")


def test_a_manager_cannot_read_another_employers_submission():
    with pytest.raises(Refused):
        service().get(MANAGER, "sb-3")


def test_a_filing_already_taken_cannot_be_sent_again():
    with pytest.raises(Refused, match="already been taken"):
        service().send(MANAGER, SendSubmission(
            filing_id="fl-1", sent_on="2025-05-14", reference="RTI/2025/0009",
            accepted=True))


def test_a_filing_nobody_sent_cannot_be_submitted_for():
    with pytest.raises(NotFound, match="filing fl-9 was not found"):
        service().send(BUREAU, SendSubmission(
            filing_id="fl-9", sent_on="2025-05-14", reference="RTI/2025/0009",
            accepted=True))


def test_what_stands_on_a_filing_is_reported():
    answer = service().standing(MANAGER, "fl-1")
    assert answer["attempts"] == 1 and answer["settled"] is True


def test_the_standing_reference_is_reported():
    assert service().standing(MANAGER, "fl-2")["standing_reference"] == "RTI/2025/0002"


def client():
    return build_client(a_store())


def test_the_route_lists_submissions():
    assert client().get("/submissions", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_what_stands_on_a_filing():
    answer = client().get("/submissions/standing/fl-1", headers=headers(MANAGER))
    assert answer.json()["settled"] is True


def test_the_route_answers_404_for_a_submission_nobody_sent():
    assert client().get("/submissions/sb-9", headers=headers(BUREAU)).status_code == 404


def test_the_route_answers_400_for_a_filing_already_taken():
    answer = client().post("/submissions", headers=headers(MANAGER), json={
        "filing_id": "fl-1", "sent_on": "2025-05-14", "reference": "RTI/2025/0009",
        "accepted": True})
    assert answer.status_code == 400
