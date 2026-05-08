"""Reading what has been sent, and what the Revenue made of it."""

from tare.common.types import Submission


def sort_by_sent(rows: list[Submission]) -> list[Submission]:
    return sorted(rows, key=lambda row: (row.sent_on, row.id))


def for_filing(rows: list[Submission], filing_id: str) -> list[Submission]:
    return sort_by_sent([row for row in rows if row.filing_id == filing_id])


def latest_for(rows: list[Submission], filing_id: str) -> Submission | None:
    """The attempt that stands for a filing.

    A filing may be sent more than once; what counts is the attempt that
    settles it.
    """
    theirs = for_filing(rows, filing_id)
    return theirs[0] if theirs else None


def is_settled(rows: list[Submission], filing_id: str) -> bool:
    """Whether the Revenue has taken the filing."""
    latest = latest_for(rows, filing_id)
    return latest is not None and latest.accepted


def attempts_on(rows: list[Submission], filing_id: str) -> int:
    return len(for_filing(rows, filing_id))
