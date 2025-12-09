"""What a run of pay entries comes to, and what each part of it counts towards."""

from dataclasses import dataclass

from tare.common.types import PayElement

#: What an element does to what is owed.
PAYMENT = "payment"
DEDUCTION = "deduction"
KINDS = (PAYMENT, DEDUCTION)


@dataclass(frozen=True)
class Entry:
    """One figure against one element, as it would read on a payslip."""

    element_id: str
    amount: int


def sort_by_code(rows: list[PayElement]) -> list[PayElement]:
    return sorted(rows, key=lambda row: row.code)


def by_id(rows: list[PayElement]) -> dict[str, PayElement]:
    return {row.id: row for row in rows}


def is_payment(row: PayElement) -> bool:
    return row.kind == PAYMENT


def gross_total(entries: list[Entry], elements: list[PayElement]) -> int:
    """What the payments on a payslip come to, before anything is taken off."""
    known = by_id(elements)
    return sum(entry.amount for entry in entries
               if entry.element_id in known and is_payment(known[entry.element_id]))


def deduction_total(entries: list[Entry], elements: list[PayElement]) -> int:
    """What the deductions come to."""
    known = by_id(elements)
    return sum(entry.amount for entry in entries
               if entry.element_id in known and not is_payment(known[entry.element_id]))


def taxable_total(entries: list[Entry], elements: list[PayElement]) -> int:
    """The figure the levy is worked out on.

    Only payments carrying the taxable flag count towards it.
    """
    known = by_id(elements)
    return sum(entry.amount for entry in entries
               if entry.element_id in known
               and known[entry.element_id].taxable
               and is_payment(known[entry.element_id])
               and entry.amount > 0)


def contributory_total(entries: list[Entry], elements: list[PayElement]) -> int:
    """The figure contributions are worked out on."""
    known = by_id(elements)
    return sum(entry.amount for entry in entries
               if entry.element_id in known
               and known[entry.element_id].contributory
               and is_payment(known[entry.element_id]))


def pensionable_total(entries: list[Entry], elements: list[PayElement]) -> int:
    """The figure a pension contribution is worked out on."""
    known = by_id(elements)
    return sum(entry.amount for entry in entries
               if entry.element_id in known
               and known[entry.element_id].pensionable
               and is_payment(known[entry.element_id]))
