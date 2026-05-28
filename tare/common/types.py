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


@dataclass
class Entitlement(Row):
    """How many days of leave somebody has for one leave year.

    `days` is what a whole year of the contract carries. `carried_in` is what
    came over from the year before.
    """

    employee_id: str
    employer_id: str
    year_starts_on: str
    days: int
    carried_in: int


@dataclass
class Suspension(Row):
    """A run of periods a deduction is held off somebody's pay.

    A deduction that cannot be taken — because the pay is not there, or because
    an order outranks it — is suspended rather than lost.
    """

    employee_id: str
    employer_id: str
    element_id: str
    reason: str
    from_period: int
    to_period: int | None
    year_starts_on: str


@dataclass
class PayRate(Row):
    """What one person is paid for one element.

    `basis` says how `amount` reads: a fixed sum for the period, a sum for each
    hour, or a multiple of the contract's own hourly rate in basis points.
    """

    employee_id: str
    employer_id: str
    element_id: str
    basis: str
    amount: int
    effective_from: str


@dataclass
class DeductionInstruction(Row):
    """A standing instruction to take something off somebody's pay.

    `priority` decides what is taken first when there is not enough to go
    round: the lower the number, the earlier it is taken.
    """

    employee_id: str
    employer_id: str
    element_id: str
    basis: str
    amount: int
    priority: int
    from_period: int
    to_period: int | None
    year_starts_on: str


@dataclass
class Payslip(Row):
    """What one person was paid for one period, as it was worked out.

    A payslip is written once, when the run it belongs to is committed, and is
    never changed after: a correction is a later payslip, not an edit to this
    one.
    """

    run_id: str
    employee_id: str
    employer_id: str
    period: int
    start: str
    end: str
    gross: int
    taxable: int
    free_pay: int
    levy: int
    contributory: int
    contributions: int
    deductions: int
    net: int


@dataclass
class PayslipLine(Row):
    """One line on a payslip, in the order it was worked out."""

    payslip_id: str
    element_id: str
    kind: str
    hours: int
    amount: int


@dataclass
class PayrollRun(Row):
    """One pass of the payroll over one employer's period."""

    employer_id: str
    calendar_id: str
    period: int
    status: str
    opened_on: str
    committed_on: str | None


@dataclass
class Region(Row):
    """A part of the country, for reporting and for regional allowances."""

    code: str
    name: str


@dataclass
class Site(Row):
    """Somewhere an employer's people actually work."""

    employer_id: str
    region_id: str
    code: str
    name: str
    closed: bool


@dataclass
class Premium(Row):
    """An uplift for working at a time somebody would rather not.

    `rate_basis_points` is what goes on top of the ordinary hourly rate, so
    5000 is time and a half of the uplift alone.
    """

    employer_id: str
    code: str
    name: str
    rate_basis_points: int
    from_hour: int
    to_hour: int
    weekend_only: bool


@dataclass
class Allowance(Row):
    """A flat sum somebody is paid every period for something."""

    employee_id: str
    employer_id: str
    element_id: str
    amount: int
    starts_on: str
    ends_on: str | None


@dataclass
class EarningsOrder(Row):
    """A court order to take money out of somebody's pay.

    `total` is what the order is for in all; `per_period` is what it asks for
    each time. `collected` is what has been taken so far.
    """

    employee_id: str
    employer_id: str
    reference: str
    total: int
    per_period: int
    collected: int
    priority: int
    made_on: str
    discharged_on: str | None


@dataclass
class ProtectedEarnings(Row):
    """The figure an order may not take somebody's pay below."""

    employee_id: str
    employer_id: str
    floor: int
    starts_on: str
    ends_on: str | None


@dataclass
class Provider(Row):
    """Somebody the bureau sends money to on an employee's behalf."""

    code: str
    name: str
    kind: str
    account: str


@dataclass
class PensionScheme(Row):
    """A scheme an employer runs, and what it takes from each side."""

    employer_id: str
    provider_id: str
    code: str
    name: str
    employee_basis_points: int
    employer_basis_points: int
    qualifying_floor: int
    opened_on: str
    closed_on: str | None


@dataclass
class Mandate(Row):
    """Where somebody's pay is sent, and from when."""

    employee_id: str
    employer_id: str
    account: str
    holder: str
    starts_on: str
    ends_on: str | None


@dataclass
class PaymentInstruction(Row):
    """One line of a payment run: who is paid, how much, into what."""

    run_id: str
    employee_id: str
    employer_id: str
    account: str
    amount: int
    status: str
    issued_on: str
    settled_on: str | None


@dataclass
class ExpenseClaim(Row):
    """Something somebody paid for and wants back."""

    employee_id: str
    employer_id: str
    element_id: str
    kind: str
    amount: int
    incurred_on: str
    claimed_on: str
    status: str


@dataclass
class Journey(Row):
    """A trip somebody made in their own car, and what it is worth."""

    employee_id: str
    employer_id: str
    travelled_on: str
    miles: int
    reason: str
    approved: bool


@dataclass
class BenefitClass(Row):
    """A kind of benefit an employer provides, and how it is valued."""

    employer_id: str
    code: str
    name: str
    basis: str
    annual_value: int


@dataclass
class BenefitAward(Row):
    """One person's use of a benefit, and what they put toward it."""

    employee_id: str
    employer_id: str
    class_id: str
    contribution: int
    starts_on: str
    ends_on: str | None


@dataclass
class ServiceRecord(Row):
    """A run of employment, which may or may not join up with the one before."""

    employee_id: str
    employer_id: str
    started_on: str
    ended_on: str | None
    reason: str


@dataclass
class AuditEntry(Row):
    """Who did what, and when. Written once and never changed."""

    operator_id: str
    operator_name: str
    employer_id: str | None
    action: str
    subject: str
    happened_on: str


@dataclass
class Notice(Row):
    """A letter the bureau sends somebody."""

    employee_id: str
    employer_id: str
    kind: str
    subject: str
    raised_on: str
    sent_on: str | None


@dataclass
class ArchiveEntry(Row):
    """A run put beyond further change, and the day it was closed off."""

    employer_id: str
    run_id: str
    closed_on: str
    payslips: int
    net: int


@dataclass
class JournalLine(Row):
    """One side of one posting from a payroll run to the nominal ledger."""

    run_id: str
    employer_id: str
    account: str
    cost_centre_id: str | None
    debit: int
    credit: int
    narrative: str


@dataclass
class LoanPlan(Row):
    """A graduate contribution plan somebody is repaying through the payroll."""

    employee_id: str
    employer_id: str
    reference: str
    plan_type: str
    total: int
    collected: int
    period_threshold: int
    rate_basis_points: int
    started_on: str
    settled_on: str | None


@dataclass
class Remittance(Row):
    """What the bureau owes one provider for one run."""

    run_id: str
    employer_id: str
    provider_id: str
    amount: int
    due_on: str
    sent_on: str | None


@dataclass
class PayReview(Row):
    """A round of pay awards an employer runs across its people."""

    employer_id: str
    reference: str
    effective_from: str
    opened_on: str
    closed_on: str | None


@dataclass
class PayAward(Row):
    """What one person got out of a review."""

    review_id: str
    employee_id: str
    employer_id: str
    basis: str
    amount: int
    old_salary: int
    new_salary: int


@dataclass
class EmployerGroup(Row):
    """Employers that belong together for transfers and for reporting."""

    code: str
    name: str


@dataclass
class GroupMembership(Row):
    """One employer's place in one group, and from when."""

    group_id: str
    employer_id: str
    joined_on: str
    left_on: str | None


@dataclass
class ServiceTransfer(Row):
    """Somebody moving from one employer to another."""

    employee_id: str
    from_employer_id: str
    to_employer_id: str
    kind: str
    effective_on: str
    accepted_on: str | None


@dataclass
class Engagement(Row):
    """Somebody working through an intermediary rather than on the payroll."""

    employer_id: str
    worker_name: str
    intermediary: str
    supervised: bool
    substitution_allowed: bool
    started_on: str
    ended_on: str | None


@dataclass
class Determination(Row):
    """What an engagement was decided to be, and what it is deemed to pay."""

    engagement_id: str
    employer_id: str
    inside: bool
    fee: int
    allowable_expenses: int
    deemed_payment: int
    decided_on: str


@dataclass
class Filing(Row):
    """A return the bureau owes the Revenue for one period."""

    employer_id: str
    run_id: str
    period: int
    period_end: str
    due_on: str
    gross: int
    levy: int
    contributions: int


@dataclass
class Submission(Row):
    """One attempt at sending a filing, and what came back."""

    filing_id: str
    employer_id: str
    sent_on: str
    reference: str
    accepted: bool
    note: str


@dataclass
class CarriedBalance(Row):
    """What a deduction could not take, held over to a later period."""

    employee_id: str
    employer_id: str
    element_id: str
    year_starts_on: str
    period: int
    shortfall: int
    carried: int
    cleared_on: str | None


@dataclass
class YearEndStatement(Row):
    """What one person was paid across a whole pay year."""

    employee_id: str
    employer_id: str
    year_starts_on: str
    year_ends_on: str
    gross: int
    levy: int
    contributions: int
    net: int
    issued_on: str | None


# ---------------------------------------------------------------------------
# Rows the warehouse loads that no area writes yet.
#
# Each of these is a shape the bureau has agreed with the Revenue and with the
# employers, and each is read back through `registry`. Nothing in the service
# puts a row in one: the work that would is not built.
# ---------------------------------------------------------------------------


@dataclass
class Attachment(Row):
    """Money taken under a court order, as it fell in one period."""

    employee_id: str
    order_id: str
    period: int
    year_starts_on: str
    asked: int
    taken: int
    protected_shortfall: int


@dataclass
class AveragedPay(Row):
    """The average a week of leave is paid at, over a reference window."""

    employee_id: str
    reference_from: str
    reference_to: str
    weeks_counted: int
    weeks_skipped: int
    weekly_average: int


@dataclass
class SickPeriod(Row):
    """A spell of sickness as statutory pay sees it."""

    employee_id: str
    absence_id: str
    waiting_days: int
    payable_days: int
    weekly_rate: int
    paid: int


@dataclass
class SacrificeAgreement(Row):
    """Pay somebody has given up, and what it buys."""

    employee_id: str
    element_id: str
    amount: int
    towards: str
    starts_on: str
    ends_on: str | None


@dataclass
class BandingBasis(Row):
    """Which basis somebody's contributions are worked out on."""

    employee_id: str
    year_starts_on: str
    basis: str
    changed_in_period: int | None


@dataclass
class BackPayAward(Row):
    """An award reaching back over periods already closed."""

    employee_id: str
    review_id: str
    from_period: int
    to_period: int
    old_rate: int
    new_rate: int
    arrears: int


@dataclass
class TerminationPayment(Row):
    """What somebody is owed on the way out."""

    employee_id: str
    left_on: str
    notice_weeks: int
    notice_pay: int
    redundancy: int
    taxable_part: int
    free_part: int


@dataclass
class PremiumEntry(Row):
    """Hours worked at a premium, and what the uplift came to."""

    employee_id: str
    premium_id: str
    worked_on: str
    hours: int
    uplift: int


@dataclass
class Apportionment(Row):
    """One cost centre's share of a run."""

    run_id: str
    cost_centre_id: str
    weight: int
    share: int


@dataclass
class RecoveryPlan(Row):
    """An overpayment being taken back over later periods."""

    employee_id: str
    overpaid_in_period: int
    year_starts_on: str
    total: int
    per_period: int
    recovered: int


@dataclass
class EnrolmentAssessment(Row):
    """What a scheme assessment decided about somebody."""

    employee_id: str
    scheme_id: str
    assessed_on: str
    qualifying_pay: int
    outcome: str
    postponed_to: str | None


@dataclass
class MileageClaim(Row):
    """A run of journeys claimed together."""

    employee_id: str
    from_day: str
    to_day: str
    miles: int
    higher_rate_miles: int
    lower_rate_miles: int
    paid: int


@dataclass
class PayrolledBenefit(Row):
    """A benefit taken through the payroll rather than reported after the year."""

    employee_id: str
    award_id: str
    period: int
    year_starts_on: str
    cash_equivalent: int
    contribution: int


@dataclass
class LoanDeduction(Row):
    """A graduate contribution as it fell in one period."""

    employee_id: str
    plan_id: str
    period: int
    year_starts_on: str
    pay_above_threshold: int
    taken: int


@dataclass
class PaymentInstructionFile(Row):
    """A file of payment instructions handed to the bank."""

    run_id: str
    employer_id: str
    reference: str
    instructions: int
    total: int
    sent_on: str | None


@dataclass
class YearEndStatementLine(Row):
    """One line of a year-end statement, as the Revenue wants it broken down."""

    statement_id: str
    element_code: str
    description: str
    amount: int


@dataclass
class ServiceTransferRecord(Row):
    """What a transfer carried across with the person."""

    transfer_id: str
    employee_id: str
    continuous_from: str
    leave_carried: int
    balances_carried: int


@dataclass
class DeemedPayment(Row):
    """A deemed payment as it fell in one period."""

    determination_id: str
    period: int
    year_starts_on: str
    fee: int
    allowance: int
    deemed: int


@dataclass
class CarriedDeduction(Row):
    """A deduction carried into a later period, as it was finally taken."""

    balance_id: str
    period: int
    year_starts_on: str
    carried_in: int
    taken: int
    carried_out: int


@dataclass
class PayAwardLine(Row):
    """One person's line in a review, before the award is settled."""

    review_id: str
    employee_id: str
    proposed_basis: str
    proposed_amount: int
    approved: bool
