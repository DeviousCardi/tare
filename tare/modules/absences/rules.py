"""What an absence covers, and when two of them are really one."""

from tare.common.dates import compare_dates, days_inclusive, overlaps, within_window
from tare.common.types import Absence

#: What somebody can be away for.
SICK = "sick"
PARENTAL = "parental"
UNPAID = "unpaid"
OTHER = "other"
KINDS = (SICK, PARENTAL, UNPAID, OTHER)

#: Two runs of sickness this close together are treated as one spell.
LINK_DAYS = 56


def sort_by_start(rows: list[Absence]) -> list[Absence]:
    return sorted(rows, key=lambda row: (row.starts_on, row.id))


def days_of(row: Absence) -> int:
    """How long the absence ran, counting both ends."""
    return days_inclusive(row.starts_on, row.ends_on)


def covers(row: Absence, day: str) -> bool:
    return within_window(day, row.starts_on, row.ends_on)


def clashes_with(row: Absence, other: Absence) -> bool:
    """Whether two absences share any day at all."""
    return overlaps(row.starts_on, row.ends_on, other.starts_on, other.ends_on)


def gap_between(earlier: Absence, later: Absence) -> int:
    """Days between the end of one absence and the start of the next.

    Touching absences have a gap of nothing. A later absence that starts before
    the earlier one ended has no gap either.
    """
    if compare_dates(later.starts_on, earlier.ends_on) <= 0:
        return 0
    return days_inclusive(earlier.ends_on, later.starts_on) - 2


def are_linked(earlier: Absence, later: Absence) -> bool:
    """Whether two spells of sickness count as one.

    Only sickness links, and only when the two runs fall close enough together.
    """
    if earlier.kind != SICK or later.kind != SICK:
        return False
    return gap_between(earlier, later) < LINK_DAYS


def spell_of(rows: list[Absence], absence: Absence) -> list[Absence]:
    """Every absence linked into one spell with this one, earliest first."""
    ordered = sort_by_start([row for row in rows
                             if row.employee_id == absence.employee_id])
    spell = [absence]
    for row in ordered:
        if row.id == absence.id:
            continue
        if compare_dates(row.starts_on, absence.starts_on) < 0:
            if are_linked(row, absence):
                spell.append(row)
        elif are_linked(absence, row):
            spell.append(row)
    return sort_by_start(spell)


def days_between(rows: list[Absence], start: str, end: str, kind: str | None = None) -> int:
    """How many days of absence fall in a window, counting both ends."""
    total = 0
    for row in rows:
        if kind and row.kind != kind:
            continue
        first = row.starts_on if compare_dates(row.starts_on, start) >= 0 else start
        last = row.ends_on if compare_dates(row.ends_on, end) <= 0 else end
        if compare_dates(first, last) <= 0 and overlaps(
                row.starts_on, row.ends_on, start, end):
            total += days_inclusive(first, last)
    return total
