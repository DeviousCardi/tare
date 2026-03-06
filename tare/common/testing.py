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
        ("bd-7", "LEVY", 0, 312500, 2000, "2024-04-06"),
        ("bd-8", "LEVY", 312501, None, 4000, "2024-04-06"),
        ("bd-9", "LEVY", 0, 320000, 2000, "2025-04-06"),
        ("bd-10", "LEVY", 320001, None, 4000, "2025-04-06"),
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


def seed_departments(store: Store) -> None:
    """A two-level tree at em-1, and one department at em-2."""
    from tare.common.types import Department

    rows = [
        ("dp-1", "em-1", "OPS", "Operations", None),
        ("dp-2", "em-1", "OPS-JOI", "Joinery", "dp-1"),
        ("dp-3", "em-1", "ADM", "Administration", None),
        ("dp-4", "em-2", "HAU", "Haulage", None),
    ]
    for row in rows:
        store.departments.insert(Department(
            id=row[0], employer_id=row[1], code=row[2], name=row[3], parent_id=row[4]))


def seed_cost_centres(store: Store) -> None:
    """Three at em-1, one of them closed, and one at em-2."""
    from tare.common.types import CostCentre

    rows = [
        ("cc-1", "em-1", "OPS01", "Workshop", "dp-2", False),
        ("cc-2", "em-1", "OPS02", "Yard", "dp-1", False),
        ("cc-3", "em-1", "ADM01", "Office", "dp-3", True),
        ("cc-4", "em-2", "HAU01", "Depot", "dp-4", False),
    ]
    for row in rows:
        store.cost_centres.insert(CostCentre(
            id=row[0], employer_id=row[1], code=row[2], name=row[3],
            department_id=row[4], closed=row[5]))


def seed_positions(store: Store) -> None:
    """A post each for the people who are still in post, and one that ended."""
    from tare.common.types import Position

    rows = [
        ("ps-1", "ee-1", "em-1", "dp-2", "cc-1", "Bench joiner", "2020-04-06", None),
        ("ps-2", "ee-2", "em-1", "dp-1", "cc-2", "Yard hand", "2025-07-01", None),
        ("ps-3", "ee-3", "em-1", "dp-3", "cc-2", "Clerk", "2021-01-11", "2025-05-31"),
        ("ps-4", "ee-4", "em-2", "dp-4", "cc-4", "Driver", "2024-03-01", None),
    ]
    for row in rows:
        store.positions.insert(Position(
            id=row[0], employee_id=row[1], employer_id=row[2], department_id=row[3],
            cost_centre_id=row[4], title=row[5], held_from=row[6], held_to=row[7]))


def seed_calendars(store: Store) -> None:
    """A monthly calendar at em-1 and a weekly one, both from 2025-04-06."""
    from tare.common.types import PayCalendar

    rows = [
        ("pc-1", "em-1", "monthly", "2025-04-06", 12),
        ("pc-2", "em-1", "weekly", "2025-04-06", 52),
        ("pc-3", "em-2", "monthly", "2025-04-06", 12),
    ]
    for row in rows:
        store.calendars.insert(PayCalendar(
            id=row[0], employer_id=row[1], frequency=row[2],
            year_starts_on=row[3], periods=row[4]))


def seed_elements(store: Store) -> None:
    """The elements a payslip is built from, at both employers."""
    from tare.common.types import PayElement

    rows = [
        ("el-1", "em-1", "BASIC", "Basic pay", "payment", True, True, True),
        ("el-2", "em-1", "OT", "Overtime", "payment", True, True, False),
        ("el-3", "em-1", "EXP", "Expenses", "payment", False, False, False),
        ("el-4", "em-1", "UNION", "Union subscription", "deduction", False, False, False),
        ("el-5", "em-2", "BASIC", "Basic pay", "payment", True, True, True),
    ]
    for row in rows:
        store.elements.insert(PayElement(
            id=row[0], employer_id=row[1], code=row[2], name=row[3], kind=row[4],
            taxable=row[5], contributory=row[6], pensionable=row[7]))


def seed_scale_points(store: Store) -> None:
    """A four-point scale, republished at a higher figure for 2025-04-06."""
    from tare.common.types import ScalePoint

    rows = [
        ("sp-1", "CRAFT", 1, 2190000, "2024-04-06"),
        ("sp-2", "CRAFT", 2, 2372500, "2024-04-06"),
        ("sp-3", "CRAFT", 3, 2555000, "2024-04-06"),
        ("sp-4", "CRAFT", 4, 2737500, "2024-04-06"),
        ("sp-5", "CRAFT", 1, 2263500, "2025-04-06"),
        ("sp-6", "CRAFT", 2, 2445000, "2025-04-06"),
        ("sp-7", "CRAFT", 3, 2628500, "2025-04-06"),
        ("sp-8", "CRAFT", 4, 2810000, "2025-04-06"),
    ]
    for row in rows:
        store.scale_points.insert(ScalePoint(
            id=row[0], scale_code=row[1], point=row[2], annual_salary=row[3],
            effective_from=row[4]))


def seed_grades(store: Store) -> None:
    """Two grades on the craft scale at em-1, and one at em-2."""
    from tare.common.types import Grade

    rows = [
        ("gr-1", "em-1", "C1", "Craft entry", "CRAFT", 1, 3),
        ("gr-2", "em-1", "C2", "Craft senior", "CRAFT", 3, 5),
        ("gr-3", "em-2", "D1", "Driver", "CRAFT", 2, 4),
    ]
    for row in rows:
        store.grades.insert(Grade(
            id=row[0], employer_id=row[1], code=row[2], name=row[3],
            scale_code=row[4], lowest_point=row[5], highest_point=row[6]))


def seed_patterns(store: Store) -> None:
    """A full week, a part week, and one at the other employer.

    Every seeded pattern is worked Monday to Friday; the weekend figures are
    nil, which is what a bureau sees on nearly every contract it runs.
    """
    from tare.common.types import WorkingPattern

    rows = [
        ("wp-1", "ee-1", "em-1", "2020-04-06", None, [8, 8, 8, 8, 5, 0, 0]),
        ("wp-2", "ee-2", "em-1", "2025-07-01", None, [4, 4, 4, 4, 4, 0, 0]),
        ("wp-3", "ee-4", "em-2", "2024-03-01", None, [8, 8, 8, 8, 5, 0, 0]),
    ]
    for row in rows:
        store.patterns.insert(WorkingPattern(
            id=row[0], employee_id=row[1], employer_id=row[2], starts_on=row[3],
            ends_on=row[4], hours=list(row[5])))


def seed_timesheets(store: Store) -> None:
    """A working week for ee-1, one line still waiting on approval."""
    from tare.common.types import TimesheetLine

    rows = [
        ("ts-1", "ee-1", "em-1", "2025-06-02", 8, "el-1", True),
        ("ts-2", "ee-1", "em-1", "2025-06-03", 8, "el-1", True),
        ("ts-3", "ee-1", "em-1", "2025-06-04", 8, "el-1", True),
        ("ts-4", "ee-1", "em-1", "2025-06-05", 3, "el-2", True),
        ("ts-5", "ee-1", "em-1", "2025-06-06", 5, "el-1", False),
        ("ts-6", "ee-4", "em-2", "2025-06-02", 8, "el-5", True),
    ]
    for row in rows:
        store.timesheets.insert(TimesheetLine(
            id=row[0], employee_id=row[1], employer_id=row[2], worked_on=row[3],
            hours=row[4], element_id=row[5], approved=row[6]))


def seed_absences(store: Store) -> None:
    """Two spells of sickness far apart, one close pair, and one parental run."""
    from tare.common.types import Absence

    rows = [
        ("ab-1", "ee-1", "em-1", "sick", "2025-01-06", "2025-01-10", "2025-01-06"),
        ("ab-2", "ee-1", "em-1", "sick", "2025-01-20", "2025-01-24", "2025-01-20"),
        ("ab-3", "ee-1", "em-1", "sick", "2025-09-01", "2025-09-05", "2025-09-01"),
        ("ab-4", "ee-2", "em-1", "parental", "2025-08-04", "2025-08-29", "2025-07-01"),
        ("ab-5", "ee-4", "em-2", "sick", "2025-03-03", "2025-03-07", "2025-03-03"),
    ]
    for row in rows:
        store.absences.insert(Absence(
            id=row[0], employee_id=row[1], employer_id=row[2], kind=row[3],
            starts_on=row[4], ends_on=row[5], notified_on=row[6]))


def seed_leave(store: Store) -> None:
    """Two granted runs inside one working week each, one still waiting."""
    from tare.common.types import LeaveRequest

    rows = [
        ("lv-1", "ee-1", "em-1", "2025-06-02", "2025-06-06", "2025-05-01", "granted"),
        ("lv-2", "ee-1", "em-1", "2025-07-07", "2025-07-11", "2025-06-01", "granted"),
        ("lv-3", "ee-1", "em-1", "2025-10-06", "2025-10-10", "2025-09-01", "asked"),
        ("lv-4", "ee-4", "em-2", "2025-06-02", "2025-06-06", "2025-05-01", "granted"),
    ]
    for row in rows:
        store.leave.insert(LeaveRequest(
            id=row[0], employee_id=row[1], employer_id=row[2], starts_on=row[3],
            ends_on=row[4], asked_on=row[5], status=row[6]))


def seed_entitlements(store: Store) -> None:
    """A leave year each for the people employed across the whole of it."""
    from tare.common.types import Entitlement

    rows = [
        ("en-1", "ee-1", "em-1", "2025-01-01", 25, 3),
        ("en-2", "ee-1", "em-1", "2024-01-01", 25, 0),
        ("en-3", "ee-4", "em-2", "2025-01-01", 28, 0),
    ]
    for row in rows:
        store.entitlements.insert(Entitlement(
            id=row[0], employee_id=row[1], employer_id=row[2],
            year_starts_on=row[3], days=row[4], carried_in=row[5]))


def seed_suspensions(store: Store) -> None:
    """One suspension still running and one already lifted."""
    from tare.common.types import Suspension

    rows = [
        ("su-1", "ee-1", "em-1", "el-4", "no pay to take it from", 3, None, "2025-04-06"),
        ("su-2", "ee-2", "em-1", "el-4", "the employee asked", 1, 2, "2025-04-06"),
    ]
    for row in rows:
        store.suspensions.insert(Suspension(
            id=row[0], employee_id=row[1], employer_id=row[2], element_id=row[3],
            reason=row[4], from_period=row[5], to_period=row[6], year_starts_on=row[7]))


def seed_rates(store: Store) -> None:
    """A fixed basic rate, an overtime multiple, and one raised part-way."""
    from tare.common.types import PayRate

    rows = [
        ("rt-1", "ee-1", "em-1", "el-1", "fixed", 260000, "2024-04-06"),
        ("rt-2", "ee-1", "em-1", "el-1", "fixed", 268000, "2025-04-06"),
        ("rt-3", "ee-1", "em-1", "el-2", "multiple", 15000, "2024-04-06"),
        ("rt-4", "ee-2", "em-1", "el-1", "hourly", 1400, "2025-07-01"),
    ]
    for row in rows:
        store.rates.insert(PayRate(
            id=row[0], employee_id=row[1], employer_id=row[2], element_id=row[3],
            basis=row[4], amount=row[5], effective_from=row[6]))


def seed_deductions(store: Store) -> None:
    """A union subscription for two people, one of them stopped part-way."""
    from tare.common.types import DeductionInstruction

    rows = [
        ("dd-1", "ee-1", "em-1", "el-4", "fixed", 1500, 50, 1, None, "2025-04-06"),
        ("dd-2", "ee-2", "em-1", "el-4", "share", 100, 60, 1, 6, "2025-04-06"),
    ]
    for row in rows:
        store.deductions.insert(DeductionInstruction(
            id=row[0], employee_id=row[1], employer_id=row[2], element_id=row[3],
            basis=row[4], amount=row[5], priority=row[6], from_period=row[7],
            to_period=row[8], year_starts_on=row[9]))


def seed_payslips(store: Store) -> None:
    """Two committed periods for ee-1 and one for ee-4."""
    from tare.common.types import Payslip, PayslipLine

    rows = [
        ("ps-slip-1", "rn-1", "ee-1", "em-1", 1, "2025-04-06", "2025-05-05",
         268000, 268000, 108000, 32000, 268000, 12800, 1500, 221700),
        ("ps-slip-2", "rn-2", "ee-1", "em-1", 2, "2025-05-06", "2025-06-05",
         275299, 275299, 216000, 11860, 275299, 13384, 1500, 248555),
        ("ps-slip-3", "rn-3", "ee-4", "em-2", 1, "2025-04-06", "2025-05-05",
         346666, 346666, 108000, 47733, 346666, 19093, 0, 279840),
    ]
    for row in rows:
        store.payslips.insert(Payslip(
            id=row[0], run_id=row[1], employee_id=row[2], employer_id=row[3],
            period=row[4], start=row[5], end=row[6], gross=row[7], taxable=row[8],
            free_pay=row[9], levy=row[10], contributory=row[11],
            contributions=row[12], deductions=row[13], net=row[14]))
    lines = [
        ("pl-1", "ps-slip-1", "el-1", "payment", 0, 268000),
        ("pl-2", "ps-slip-1", "el-4", "deduction", 0, 1500),
        ("pl-3", "ps-slip-2", "el-1", "payment", 0, 268000),
        ("pl-4", "ps-slip-2", "el-2", "payment", 3, 7299),
        ("pl-5", "ps-slip-2", "el-4", "deduction", 0, 1500),
    ]
    for row in lines:
        store.payslip_lines.insert(PayslipLine(
            id=row[0], payslip_id=row[1], element_id=row[2], kind=row[3],
            hours=row[4], amount=row[5]))


def seed_regions(store: Store) -> None:
    """Three regions, which is enough for a site in each and one spare."""
    from tare.common.types import Region

    for row in (("rg-1", "N", "North"), ("rg-2", "S", "South"), ("rg-3", "W", "West")):
        store.regions.insert(Region(id=row[0], code=row[1], name=row[2]))


def seed_sites(store: Store) -> None:
    """Two sites at em-1, one of them closed, and one at em-2."""
    from tare.common.types import Site

    rows = [
        ("st-1", "em-1", "rg-1", "HAL", "Halloway works", False),
        ("st-2", "em-1", "rg-2", "SOU", "Southern store", True),
        ("st-3", "em-2", "rg-1", "VER", "Verrin depot", False),
    ]
    for row in rows:
        store.sites.insert(Site(
            id=row[0], employer_id=row[1], region_id=row[2], code=row[3],
            name=row[4], closed=row[5]))


def seed_premiums(store: Store) -> None:
    """A night uplift that wraps past midnight, and a weekend one."""
    from tare.common.types import Premium

    rows = [
        ("pm-1", "em-1", "NIGHT", "Night shift", 3000, 22, 6, False),
        ("pm-2", "em-1", "WKND", "Weekend", 5000, 0, 23, True),
        ("pm-3", "em-2", "NIGHT", "Night shift", 2500, 22, 6, False),
    ]
    for row in rows:
        store.premiums.insert(Premium(
            id=row[0], employer_id=row[1], code=row[2], name=row[3],
            rate_basis_points=row[4], from_hour=row[5], to_hour=row[6],
            weekend_only=row[7]))


def seed_allowances(store: Store) -> None:
    """A tool allowance still running and one that has ended."""
    from tare.common.types import Allowance

    rows = [
        ("al-1", "ee-1", "em-1", "el-3", 4500, "2025-01-01", None),
        ("al-2", "ee-2", "em-1", "el-3", 2000, "2025-07-01", "2025-09-30"),
        ("al-3", "ee-4", "em-2", "el-5", 6000, "2025-01-01", None),
    ]
    for row in rows:
        store.allowances.insert(Allowance(
            id=row[0], employee_id=row[1], employer_id=row[2], element_id=row[3],
            amount=row[4], starts_on=row[5], ends_on=row[6]))


def seed_orders(store: Store) -> None:
    """Two orders whose totals divide exactly by what they ask for each period."""
    from tare.common.types import EarningsOrder

    rows = [
        ("or-1", "ee-1", "em-1", "CT/2025/0001", 60000, 5000, 15000, 10, "2025-02-01", None),
        ("or-2", "ee-2", "em-1", "CT/2025/0002", 24000, 4000, 24000, 20, "2025-03-01", None),
        ("or-3", "ee-4", "em-2", "CT/2025/0003", 30000, 3000, 0, 10, "2025-04-01", None),
    ]
    for row in rows:
        store.orders.insert(EarningsOrder(
            id=row[0], employee_id=row[1], employer_id=row[2], reference=row[3],
            total=row[4], per_period=row[5], collected=row[6], priority=row[7],
            made_on=row[8], discharged_on=row[9]))


def seed_protections(store: Store) -> None:
    """A floor each for the two people who carry an earnings order."""
    from tare.common.types import ProtectedEarnings

    rows = [
        ("pr-1", "ee-1", "em-1", 120000, "2025-02-01", None),
        ("pr-2", "ee-2", "em-1", 90000, "2025-03-01", None),
    ]
    for row in rows:
        store.protections.insert(ProtectedEarnings(
            id=row[0], employee_id=row[1], employer_id=row[2], floor=row[3],
            starts_on=row[4], ends_on=row[5]))


def seed_providers(store: Store) -> None:
    """One of each kind the bureau sends money to."""
    from tare.common.types import Provider

    rows = [
        ("pv-1", "APEX", "Apex Pensions", "pension", "20-11-45/40028761"),
        ("pv-2", "UNI", "United Trades", "union", "30-22-10/11223344"),
        ("pv-3", "COURT", "County Court", "court", "60-01-01/99887766"),
    ]
    for row in rows:
        store.providers.insert(Provider(
            id=row[0], code=row[1], name=row[2], kind=row[3], account=row[4]))


def seed_holidays(store: Store) -> None:
    """The Revenue's calendar, as far ahead as any test needs it."""
    from tare.common.types import Holiday

    for day in HOLIDAY_DATES:
        store.holidays.insert(Holiday(id="", holiday_on=day, name="Bank holiday"))
