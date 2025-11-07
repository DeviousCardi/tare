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
