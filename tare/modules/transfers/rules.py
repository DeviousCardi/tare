"""What a transfer carries with it."""

from tare.common.types import ServiceTransfer

#: Why somebody moved.
BUSINESS = "business"
WITHIN_GROUP = "within group"
NEW_START = "new start"
KINDS = (BUSINESS, WITHIN_GROUP, NEW_START)


def sort_by_effective(rows: list[ServiceTransfer]) -> list[ServiceTransfer]:
    return sorted(rows, key=lambda row: (row.effective_on, row.id))


def is_accepted(row: ServiceTransfer) -> bool:
    return row.accepted_on is not None


def service_carries(row: ServiceTransfer) -> bool:
    """Whether continuous service goes across with the person.

    A transfer of the business itself carries service with it; somebody who
    simply took a job somewhere new starts again.
    """
    return row.kind == BUSINESS


def moves_to(rows: list[ServiceTransfer], employee_id: str) -> str | None:
    """Where somebody's latest accepted transfer put them."""
    theirs = [row for row in sort_by_effective(rows)
              if row.employee_id == employee_id and is_accepted(row)]
    return theirs[-1].to_employer_id if theirs else None
