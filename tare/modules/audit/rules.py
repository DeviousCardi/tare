"""Reading the audit trail."""

from tare.common.dates import within_window
from tare.common.types import AuditEntry


def sort_by_happened(rows: list[AuditEntry]) -> list[AuditEntry]:
    """Newest first, which is the order anybody reads an audit trail in."""
    return sorted(rows, key=lambda row: (row.happened_on, row.id), reverse=True)


def between(rows: list[AuditEntry], start: str, end: str) -> list[AuditEntry]:
    return sort_by_happened([row for row in rows
                             if within_window(row.happened_on, start, end)])


def by_operator(rows: list[AuditEntry], operator_id: str) -> list[AuditEntry]:
    return sort_by_happened([row for row in rows if row.operator_id == operator_id])


def actions_taken(rows: list[AuditEntry]) -> dict[str, int]:
    """How many times each kind of thing was done, in a settled order."""
    found: dict[str, int] = {}
    for row in rows:
        found[row.action] = found.get(row.action, 0) + 1
    return dict(sorted(found.items()))
