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


def seed_employees(store: Store) -> None:
    """Four people across the two employers, spanning the cases that matter.

    One long-serving, one who joined mid-year, one who has left, and one at the
    other employer so a visibility test never has to build its own.
    """
    from tare.common.types import Employee

    rows = [
        ("ee-1", "em-1", "em-1/0001", "Nell Harrow", "2020-04-06", None, "1978-02-14", "L1"),
        ("ee-2", "em-1", "em-1/0002", "Bram Cottle", "2025-07-01", None, "1996-11-03", "L1"),
        ("ee-3", "em-1", "em-1/0003", "Joss Fenn", "2021-01-11", "2025-05-31", "1985-06-30", "L2"),
        ("ee-4", "em-2", "em-2/0001", "Wren Attley", "2024-03-01", None, "1990-09-09", "L1"),
    ]
    for row in rows:
        store.employees.insert(Employee(
            id=row[0], employer_id=row[1], reference=row[2], name=row[3],
            joined_on=row[4], left_on=row[5], date_of_birth=row[6], levy_code=row[7]))


def seed_contracts(store: Store) -> None:
    """One contract each for the people `seed_employees` puts on the payroll."""
    from tare.common.types import Contract

    rows = [
        ("ct-1", "ee-1", "em-1", "2020-04-06", None, 37, 3120000, 8),
        ("ct-2", "ee-2", "em-1", "2025-07-01", None, 20, 1560000, 4),
        ("ct-3", "ee-3", "em-1", "2021-01-11", "2025-05-31", 37, 2600000, 4),
        ("ct-4", "ee-4", "em-2", "2024-03-01", None, 37, 4160000, 12),
    ]
    for row in rows:
        store.contracts.insert(Contract(
            id=row[0], employee_id=row[1], employer_id=row[2], started_on=row[3],
            ended_on=row[4], hours_per_week=row[5], annual_salary=row[6],
            notice_weeks=row[7]))


def seed_levy_codes(store: Store) -> None:
    """Two codes, one of each basis, and one of them changed for the new year.

    L1 is the ordinary cumulative code and it goes up on 2025-04-06, which is
    what gives every test a change to read either side of.
    """
    from tare.common.types import LevyCode

    rows = [
        ("lc-1", "L1", "Ordinary allowance", 1257000, "cumulative", "2024-04-06"),
        ("lc-2", "L1", "Ordinary allowance", 1296000, "cumulative", "2025-04-06"),
        ("lc-3", "L2", "Second job, no allowance", 0, "period", "2024-04-06"),
    ]
    for row in rows:
        store.levy_codes.insert(LevyCode(
            id=row[0], code=row[1], description=row[2], annual_allowance=row[3],
            basis=row[4], effective_from=row[5]))


def seed_bands(store: Store) -> None:
    """Letter A, published once and raised for 2025-04-06.

    Three floors: nothing under the first, the main rate through the middle,
    and a lower rate on everything above the middle band's ceiling.
    """
    from tare.common.types import Band

    rows = [
        ("bd-1", "A", 0, 104000, 0, "2024-04-06"),
        ("bd-2", "A", 104001, 418000, 800, "2024-04-06"),
        ("bd-3", "A", 418001, None, 200, "2024-04-06"),
        ("bd-4", "A", 0, 108000, 0, "2025-04-06"),
        ("bd-5", "A", 108001, 425000, 800, "2025-04-06"),
        ("bd-6", "A", 425001, None, 200, "2025-04-06"),
    ]
    for row in rows:
        store.bands.insert(Band(
            id=row[0], letter=row[1], from_pay=row[2], to_pay=row[3],
            rate_basis_points=row[4], effective_from=row[5]))


def seed_thresholds(store: Store) -> None:
    """The three thresholds, monthly and weekly, raised for 2025-04-06."""
    from tare.common.types import Threshold

    rows = [
        ("th-1", "contributions_start", "monthly", 104000, "2024-04-06"),
        ("th-2", "contributions_start", "weekly", 24200, "2024-04-06"),
        ("th-3", "higher_levy_starts", "monthly", 418000, "2024-04-06"),
        ("th-4", "lower_earnings", "monthly", 52300, "2024-04-06"),
        ("th-5", "contributions_start", "monthly", 108000, "2025-04-06"),
        ("th-6", "contributions_start", "weekly", 25100, "2025-04-06"),
        ("th-7", "higher_levy_starts", "monthly", 425000, "2025-04-06"),
    ]
    for row in rows:
        store.thresholds.insert(Threshold(
            id=row[0], kind=row[1], frequency=row[2], amount=row[3],
            effective_from=row[4]))


def seed_reliefs(store: Store) -> None:
    """One flat relief and one share, with the flat one raised for 2025-04-06."""
    from tare.common.types import Relief

    rows = [
        ("rl-1", "TOOLS", "Tools and upkeep", "flat", 12000, "2024-04-06"),
        ("rl-2", "TOOLS", "Tools and upkeep", "flat", 14000, "2025-04-06"),
        ("rl-3", "UNION", "Union subscription", "share", 150, "2024-04-06"),
    ]
    for row in rows:
        store.reliefs.insert(Relief(
            id=row[0], code=row[1], description=row[2], basis=row[3],
            amount=row[4], effective_from=row[5]))


def seed_exemptions(store: Store) -> None:
    """One standing exemption, one that has ended, one at the other employer."""
    from tare.common.types import Exemption

    rows = [
        ("ex-1", "ee-1", "contributions", "Over pension age", "2025-01-01", None),
        ("ex-2", "ee-2", "loan", "Plan settled in full", "2025-07-01", "2025-08-31"),
        ("ex-3", "ee-4", "levy", "Seconded abroad", "2025-02-01", None),
    ]
    for row in rows:
        store.exemptions.insert(Exemption(
            id=row[0], employee_id=row[1], kind=row[2], reason=row[3],
            starts_on=row[4], ends_on=row[5]))


def seed_holidays(store: Store) -> None:
    """The Revenue's calendar, as far ahead as any test needs it."""
    from tare.common.types import Holiday

    for day in HOLIDAY_DATES:
        store.holidays.insert(Holiday(id="", holiday_on=day, name="Bank holiday"))
