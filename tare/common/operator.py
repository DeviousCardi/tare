"""Who may see what, and who may do what.

Two separate questions and they are answered separately. Visibility is about
one employer's rows: a clerk and a manager see their own employer and nothing
else. Authority is about the operation itself: taking on an employer,
publishing a Revenue table and opening a period are the bureau's alone, whoever
the rows belong to.

Every route asks both, without exception. A route that reads rows and forgets
to ask the first question hands one employer another's payroll.
"""

from tare.common.errors import refuse
from tare.common.types import Operator


def is_bureau(operator: Operator) -> bool:
    return operator.role == "bureau"


def sees(operator: Operator, employer_id: str) -> bool:
    """Whether this operator may see rows belonging to that employer."""
    if is_bureau(operator):
        return True
    return operator.employer_id == employer_id


def assert_sees(operator: Operator, employer_id: str) -> None:
    if not sees(operator, employer_id):
        raise refuse(f"{operator.name} cannot see employer {employer_id}")


def assert_bureau(operator: Operator, doing: str) -> None:
    """For the handful of operations only the bureau may perform at all."""
    if not is_bureau(operator):
        raise refuse(f"only the bureau may {doing}")


def visible_to(operator: Operator, rows: list, attribute: str = "employer_id") -> list:
    """Narrow a run of rows to the ones this operator may see.

    Kept here rather than in each area so that adding an area cannot forget it.
    """
    if is_bureau(operator):
        return list(rows)
    return [row for row in rows if getattr(row, attribute) == operator.employer_id]
