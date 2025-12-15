"""Which points a grade covers, and where somebody sits in it."""

from tare.common.types import Grade


def sort_by_code(rows: list[Grade]) -> list[Grade]:
    return sorted(rows, key=lambda row: row.code)


def points_covered(row: Grade) -> list[int]:
    """Every scale point this grade covers, lowest first."""
    return list(range(row.lowest_point, row.highest_point))


def covers(row: Grade, point: int) -> bool:
    """Whether a point falls inside the grade."""
    return point in points_covered(row)


def grade_holding(rows: list[Grade], scale_code: str, point: int) -> Grade | None:
    """The grade of one scale that covers a point, lowest code winning."""
    for row in sort_by_code(rows):
        if row.scale_code == scale_code and covers(row, point):
            return row
    return None


def width_of(row: Grade) -> int:
    """How many points the grade covers."""
    return len(points_covered(row))
