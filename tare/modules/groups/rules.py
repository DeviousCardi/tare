"""Which employers belong together, and when they did."""

from tare.common.dates import compare_dates, within_window
from tare.common.types import EmployerGroup, GroupMembership


def sort_by_code(rows: list[EmployerGroup]) -> list[EmployerGroup]:
    return sorted(rows, key=lambda row: row.code)


def held_on(row: GroupMembership, day: str) -> bool:
    """Whether the employer was in the group that day. The last day counts."""
    if compare_dates(day, row.joined_on) < 0:
        return False
    return row.left_on is None or within_window(day, row.joined_on, row.left_on)


def groups_of(rows: list[GroupMembership], employer_id: str, day: str) -> list[str]:
    """Every group an employer was in on a day, in a settled order."""
    return sorted({row.group_id for row in rows
                   if row.employer_id == employer_id and held_on(row, day)})


def members_of(rows: list[GroupMembership], group_id: str, day: str) -> list[str]:
    return sorted({row.employer_id for row in rows
                   if row.group_id == group_id and held_on(row, day)})


def share_a_group(rows: list[GroupMembership], one: str, other: str, day: str) -> bool:
    """Whether two employers belonged together on a day."""
    return bool(groups_of(rows, one, day)) and bool(groups_of(rows, other, day))
