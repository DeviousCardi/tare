"""Tables the Revenue publishes, and finding the row in force on a day.

Every Revenue table works the same way and it is worth saying once. A row is
effective from a date and is never edited: a change is a new row with a later
date. The row in force on a day is the latest one that had **already** taken
effect, and a row takes effect on its own effective date rather than the day
after.

Everything here works on anything carrying an `effective_from`, so a table only
has to say what its rows mean, not how they are dated.
"""

from typing import TypeVar

from tare.common.dates import compare_dates

T = TypeVar("T")


def sort_by_effective(rows: list[T]) -> list[T]:
    """Oldest first, so the last one that qualifies is the one in force."""
    return sorted(rows, key=lambda row: (row.effective_from, row.id))


def in_force_on(rows: list[T], day: str) -> T | None:
    """The latest row that had already taken effect on that day."""
    already = [row for row in sort_by_effective(rows)
               if compare_dates(row.effective_from, day) <= 0]
    return already[-1] if already else None


def all_in_force_on(rows: list[T], day: str, key) -> list[T]:
    """One row per `key`, each the latest that had taken effect on the day.

    A table keyed by something — a band letter, a code — has a row in force for
    each key at once, and this picks the right row for every key in one pass.
    """
    found: dict = {}
    for row in sort_by_effective(rows):
        if compare_dates(row.effective_from, day) <= 0:
            found[key(row)] = row
    return list(found.values())


def published_on(rows: list[T], day: str) -> list[T]:
    """Every row that took effect on exactly that day."""
    return [row for row in sort_by_effective(rows) if row.effective_from == day]
