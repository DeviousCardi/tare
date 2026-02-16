"""Reading an employer's sites."""

from tare.common.types import Site


def sort_by_code(rows: list[Site]) -> list[Site]:
    return sorted(rows, key=lambda row: row.code)


def open_sites(rows: list[Site]) -> list[Site]:
    """A closed site takes no more people."""
    return sort_by_code([row for row in rows if not row.closed])


def in_region(rows: list[Site], region_id: str) -> list[Site]:
    return sort_by_code([row for row in rows if row.region_id == region_id])


def regions_used(rows: list[Site]) -> list[str]:
    """Every region an employer has a site in, in a settled order."""
    return sorted({row.region_id for row in rows})
