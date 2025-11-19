"""Whether an exemption covered a day, worked out on its own."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import Exemption

#: What an exemption can be from.
CONTRIBUTIONS = "contributions"
LEVY = "levy"
LOAN = "loan"
KINDS = (CONTRIBUTIONS, LEVY, LOAN)


def sort_by_start(rows: list[Exemption]) -> list[Exemption]:
    return sorted(rows, key=lambda row: (row.starts_on, row.id))


def covers(row: Exemption, day: str) -> bool:
    """Whether the exemption stood on that day. Both ends count."""
    if compare_dates(day, row.starts_on) < 0:
        return False
    return row.ends_on is None or within_window(day, row.starts_on, row.ends_on)


def standing_for(
    rows: list[Exemption], employee_id: str, kind: str, day: str,
) -> Exemption | None:
    """The exemption of one kind standing for one person on a day."""
    theirs = [row for row in sort_by_start(rows)
              if row.employee_id == employee_id and row.kind == kind and covers(row, day)]
    return theirs[-1] if theirs else None


def kinds_standing(rows: list[Exemption], employee_id: str, day: str) -> list[str]:
    """Every kind this person was exempt from on a day, in a settled order."""
    found = {row.kind for row in rows
             if row.employee_id == employee_id and covers(row, day)}
    return sorted(found)
