"""What is true about a person regardless of who is asking."""

from tare.common.dates import compare_dates, days_inclusive, parse, within_window
from tare.common.types import Employee


def sort_by_reference(rows: list[Employee]) -> list[Employee]:
    return sorted(rows, key=lambda row: row.reference)


def sort_by_name(rows: list[Employee]) -> list[Employee]:
    """Surname first, the way a payroll register reads."""
    return sorted(rows, key=lambda row: (row.name.split()[-1].lower(), row.reference))


def next_reference(rows: list[Employee], employer_id: str) -> str:
    """References run per employer, so two employers both have a 0001."""
    mine = [row for row in rows if row.employer_id == employer_id]
    issued = [int(row.reference.split("/")[-1]) for row in mine if "/" in row.reference]
    return f"{employer_id}/{(max(issued) + 1 if issued else 1):04d}"


def in_post_on(row: Employee, day: str) -> bool:
    """Whether the person was on the payroll that day. The leaving day counts."""
    if compare_dates(day, row.joined_on) < 0:
        return False
    return row.left_on is None or within_window(day, row.joined_on, row.left_on)


def age_on(row: Employee, day: str) -> int:
    """Whole years old on that day. A birthday counts on the day it falls."""
    born, when = parse(row.date_of_birth), parse(day)
    years = when.year - born.year
    if (when.month, when.day) < (born.month, born.day):
        years -= 1
    return years


def days_in_post(row: Employee, upto: str) -> int:
    """How many days the person has been on the payroll, counting both ends."""
    end = row.left_on if row.left_on and compare_dates(row.left_on, upto) < 0 else upto
    if compare_dates(end, row.joined_on) < 0:
        return 0
    return days_inclusive(row.joined_on, end)
