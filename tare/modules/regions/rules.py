"""Reading the region list."""

from tare.common.types import Region


def sort_by_code(rows: list[Region]) -> list[Region]:
    return sorted(rows, key=lambda row: row.code)


def by_code(rows: list[Region], code: str) -> Region | None:
    for row in sort_by_code(rows):
        if row.code == code:
            return row
    return None


def codes_of(rows: list[Region]) -> list[str]:
    return [row.code for row in sort_by_code(rows)]
