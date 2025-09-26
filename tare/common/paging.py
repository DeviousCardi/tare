"""One shape for every listing in the service.

Every listing takes `limit` and `offset` and answers `{"data": [...],
"total": n}`. The total counts the whole match, not the page — a caller paging
through needs to know how far there is to go, and a total that only counted the
page would always equal its length and tell them nothing.
"""

from typing import Any, TypeVar

from tare.common.errors import refuse

T = TypeVar("T")

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


def page(rows: list[T], limit: int | None = None, offset: int | None = None) -> dict[str, Any]:
    """The page of `rows` a caller asked for, and how many there were in all."""
    start = 0 if offset is None else offset
    if start < 0:
        raise refuse("offset cannot be negative")
    size = DEFAULT_LIMIT if limit is None else limit
    if size < 0:
        raise refuse("limit cannot be negative")
    if size > MAX_LIMIT:
        raise refuse(f"limit cannot be more than {MAX_LIMIT}")
    return {"data": rows[start:start + size], "total": len(rows)}
