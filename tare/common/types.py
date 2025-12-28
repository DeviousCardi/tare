"""The rows the store holds, and who is asking for them.

Rows are plain dataclasses: the store keeps them, the areas read them, and
nothing validates at this layer. Validation belongs at the edge, in each area's
request models, so a rule is stated once where a caller can be told about it.

Every row has an `id`. Identifiers are short prefixed strings, never integers.
"""

from dataclasses import dataclass
from typing import Literal

Role = Literal["bureau", "manager", "clerk"]


@dataclass(frozen=True)
class Operator:
    """Who is asking.

    `employer_id` is the one employer a clerk or a manager may see. The bureau
    carries `None`, which means every employer rather than none of them.
    """

    id: str
    name: str
    role: Role
    employer_id: str | None


@dataclass
class Row:
    """Base for everything the store holds."""

    id: str


@dataclass
class Employer(Row):
    """An employer whose payroll the bureau runs."""

    reference: str
    name: str
    opened_on: str
    closed_on: str | None
    pay_day: int


@dataclass
class Employee(Row):
    """Somebody an employer pays."""

    employer_id: str
    reference: str
    name: str
    joined_on: str
    left_on: str | None
    date_of_birth: str
    levy_code: str


@dataclass
class Contract(Row):
    """The terms one person is employed on. A person may hold several in turn."""

    employee_id: str
    employer_id: str
    started_on: str
    ended_on: str | None
    hours_per_week: int
    annual_salary: int
    notice_weeks: int


@dataclass
class Holiday(Row):
    """A day the Revenue's calendar holds, so it is not a working day."""

    holiday_on: str
    name: str


@dataclass
class LevyCode(Row):
    """A levy code, and the free pay a year of it carries.

    `basis` says how the free pay is spent. A cumulative code carries the whole
    year's allowance forward, so an unused part of it is still there next
    period. A period code spends one period's worth and forgets the rest.
    """

    code: str
    description: str
    annual_allowance: int
    basis: str
    effective_from: str


@dataclass
class Band(Row):
    """One slice of pay a contribution rate applies to.

    Both bounds count. `to_pay` of `None` is the top band, which runs on
    without a ceiling.
    """

    letter: str
    from_pay: int
    to_pay: int | None
    rate_basis_points: int
    effective_from: str


@dataclass
class Threshold(Row):
    """A figure at which something starts, or stops.

    `kind` says what it governs, `frequency` which payroll it is quoted for,
    since the Revenue publishes the same threshold weekly and monthly rather
    than expecting anyone to divide it.
    """

    kind: str
    frequency: str
    amount: int
    effective_from: str


@dataclass
class Relief(Row):
    """An amount that comes off pay before the levy is worked out.

    `basis` says how it is quoted: a flat amount per period, or a share of pay
    in basis points.
    """

    code: str
    description: str
    basis: str
    amount: int
    effective_from: str


@dataclass
class Exemption(Row):
    """A reason one person is not charged something everybody else is."""

    employee_id: str
    kind: str
    reason: str
    starts_on: str
    ends_on: str | None


@dataclass
class Department(Row):
    """A part of an employer's organisation, for reporting and for cost."""

    employer_id: str
    code: str
    name: str
    parent_id: str | None


@dataclass
class CostCentre(Row):
    """Where a cost is booked when the payroll is posted to the ledger."""

    employer_id: str
    code: str
    name: str
    department_id: str | None
    closed: bool


@dataclass
class Position(Row):
    """A post somebody holds, and where its cost belongs."""

    employee_id: str
    employer_id: str
    department_id: str
    cost_centre_id: str
    title: str
    held_from: str
    held_to: str | None


@dataclass
class PayCalendar(Row):
    """When an employer's pay periods start and how many there are in a year.

    A calendar runs from `year_starts_on` for `periods` periods. Weekly and
    fortnightly periods are runs of days; monthly ones follow the calendar
    months from the day the year starts.
    """

    employer_id: str
    frequency: str
    year_starts_on: str
    periods: int


@dataclass
class PayElement(Row):
    """One named thing that can appear on a payslip.

    The three flags say what a figure of this element counts towards: the levy,
    the contributions, and the pensionable figure. They are separate because a
    thing can count towards one and not another.
    """

    employer_id: str
    code: str
    name: str
    kind: str
    taxable: bool
    contributory: bool
    pensionable: bool


@dataclass
class ScalePoint(Row):
    """One point on a pay scale, and what a year of it is worth."""

    scale_code: str
    point: int
    annual_salary: int
    effective_from: str


@dataclass
class Grade(Row):
    """A grade an employer uses, and the run of scale points it covers."""

    employer_id: str
    code: str
    name: str
    scale_code: str
    lowest_point: int
    highest_point: int


@dataclass
class WorkingPattern(Row):
    """The hours somebody is expected to work, day by day.

    `hours` runs Monday to Sunday and is held in whole hours. A pattern stands
    from `starts_on` until another replaces it.
    """

    employee_id: str
    employer_id: str
    starts_on: str
    ends_on: str | None
    hours: list[int]


@dataclass
class TimesheetLine(Row):
    """Hours somebody put in on one day, and what they are to be paid as."""

    employee_id: str
    employer_id: str
    worked_on: str
    hours: int
    element_id: str
    approved: bool


@dataclass
class Absence(Row):
    """A run of days somebody was away, and what kind of absence it was."""

    employee_id: str
    employer_id: str
    kind: str
    starts_on: str
    ends_on: str
    notified_on: str


@dataclass
class LeaveRequest(Row):
    """A run of days somebody asked to take off, and what became of it."""

    employee_id: str
    employer_id: str
    starts_on: str
    ends_on: str
    asked_on: str
    status: str
