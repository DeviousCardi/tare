"""What the suite is built on.

This ships with the service rather than living beside the tests, because it is
part of the public surface: anything written against the bureau — our own
suite, an employer's integration harness — needs a store it can fill and an
operator it can act as, and both should come from one place that moves with the
code.

Three operators, because the interesting cases are always about who is asking.
`BUREAU` sees every employer. `MANAGER` and `CLERK` both belong to `em-1`, so a
test that wants "somebody who cannot see this" has one to hand without building
another employer first.
"""

from fastapi.testclient import TestClient

from tare.app import create_app
from tare.common.store import Store
from tare.common.types import Operator

BUREAU = Operator(id="op-1", name="Rae", role="bureau", employer_id=None)
MANAGER = Operator(id="op-2", name="Sol", role="manager", employer_id="em-1")
CLERK = Operator(id="op-3", name="Ivy", role="clerk", employer_id="em-1")

#: A weekday the Revenue holds, and the two days either side of the year end.
HOLIDAY_DATES = [
    "2025-01-01", "2025-04-18", "2025-04-21", "2025-05-05", "2025-05-26",
    "2025-08-25", "2025-12-25", "2025-12-26",
    "2026-01-01", "2026-04-03", "2026-04-06", "2026-05-04", "2026-05-25",
    "2026-08-31", "2026-12-25", "2026-12-28",
]


def build_store() -> Store:
    """A store of its own, with nothing in it.

    Every test builds one. They are cheap, so nothing is shared and the order
    tests run in cannot matter.
    """
    return Store()


def build_client(store: Store | None = None) -> TestClient:
    """An application over that store, ready to be called."""
    return TestClient(create_app(store))


def headers(operator: Operator) -> dict[str, str]:
    """The header the gateway would have put on the request for that operator."""
    return {"x-bureau-operator":
            f"{operator.id}:{operator.name}:{operator.role}:{operator.employer_id or ''}"}


def seed_employers(store: Store) -> None:
    """Two employers, so a test always has one the operator cannot see.

    `em-1` is the one MANAGER and CLERK belong to. `em-2` exists purely so that
    "somebody else's rows" is one line away in any test that needs it.
    """
    from tare.common.types import Employer

    store.employers.insert(Employer(
        id="em-1", reference="E-0001", name="Halloway Joinery",
        opened_on="2024-01-01", closed_on=None, pay_day=28))
    store.employers.insert(Employer(
        id="em-2", reference="E-0002", name="Verrin Freight",
        opened_on="2024-03-01", closed_on=None, pay_day=15))


def seed_holidays(store: Store) -> None:
    """The Revenue's calendar, as far ahead as any test needs it."""
    table = getattr(store, "holidays", None)
    if table is None:
        return
    for day in HOLIDAY_DATES:
        table.insert(_holiday(day))


def _holiday(day: str):
    from tare.common.types import Row
    from dataclasses import dataclass

    @dataclass
    class _Row(Row):
        holiday_on: str

    return _Row(id="", holiday_on=day)
