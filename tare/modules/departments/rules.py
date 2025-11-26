"""How departments sit under one another."""

from tare.common.types import Department


def sort_by_code(rows: list[Department]) -> list[Department]:
    return sorted(rows, key=lambda row: row.code)


def children_of(rows: list[Department], parent_id: str | None) -> list[Department]:
    return sort_by_code([row for row in rows if row.parent_id == parent_id])


def ancestors_of(rows: list[Department], department_id: str) -> list[Department]:
    """Every department above this one, nearest first.

    Walks up by identifier and stops if it ever comes back to somewhere it has
    already been, so a cycle put in by a bad load reports what it can rather
    than hanging.
    """
    by_id = {row.id: row for row in rows}
    seen: set[str] = set()
    found: list[Department] = []
    cursor = by_id.get(department_id)
    while cursor and cursor.parent_id and cursor.parent_id not in seen:
        seen.add(cursor.parent_id)
        parent = by_id.get(cursor.parent_id)
        if not parent:
            break
        found.append(parent)
        cursor = parent
    return found


def depth_of(rows: list[Department], department_id: str) -> int:
    """How far down the tree a department sits. The top is nothing deep."""
    return len(ancestors_of(rows, department_id))


def would_make_a_cycle(rows: list[Department], department_id: str, parent_id: str) -> bool:
    """Whether putting this department under that one folds the tree onto itself."""
    if department_id == parent_id:
        return True
    return department_id in {row.id for row in ancestors_of(rows, parent_id)}
