"""Reading what has been closed off."""

from tare.common.dates import within_window
from tare.common.types import ArchiveEntry


def sort_by_closed(rows: list[ArchiveEntry]) -> list[ArchiveEntry]:
    """Newest first: the last thing closed off is the one anybody asks about."""
    return sorted(rows, key=lambda row: (row.closed_on, row.id), reverse=True)


def between(rows: list[ArchiveEntry], start: str, end: str) -> list[ArchiveEntry]:
    return sort_by_closed([row for row in rows
                           if within_window(row.closed_on, start, end)])


def holds(rows: list[ArchiveEntry], run_id: str) -> bool:
    return any(row.run_id == run_id for row in rows)


def totals_of(rows: list[ArchiveEntry]) -> dict[str, int]:
    """What the archive holds in all."""
    return {"runs": len(rows),
            "payslips": sum(row.payslips for row in rows),
            "net": sum(row.net for row in rows)}
