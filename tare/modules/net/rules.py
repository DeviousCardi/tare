"""Working a gross figure down to what is actually paid.

The order matters and it is stated once here. Free pay comes off the taxable
figure before the levy is worked out. Contributions are worked out on their own
figure and know nothing about the levy. Deductions come out of what is left
after both, which is why an instruction can fall short even when the gross
looked ample.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Worked:
    """Every figure on the way from gross to net."""

    gross: int
    taxable: int
    free_pay: int
    levyable: int
    levy: int
    contributory: int
    contributions: int
    deductions: int
    net: int


def levyable_pay(taxable: int, free_pay: int) -> int:
    """What the levy is actually charged on. It never goes below nothing."""
    return max(0, taxable - free_pay)


def net_pay(gross: int, levy: int, contributions: int, deductions: int) -> int:
    """What is handed over.

    It can reach nothing but never goes below it: a deduction that would take
    somebody into debt to their employer is the thing that falls short, not the
    payment.
    """
    return max(0, gross - levy - contributions - deductions)


def take_home_share(worked: Worked) -> int:
    """What share of the gross is actually paid, in basis points."""
    if worked.gross <= 0:
        return 0
    return round(worked.net * 10000 / worked.gross)


def assemble(
    gross: int, taxable: int, free_pay: int, levy: int, contributory: int,
    contributions: int, deductions: int,
) -> Worked:
    levyable = levyable_pay(taxable, free_pay)
    return Worked(
        gross=gross, taxable=taxable, free_pay=free_pay, levyable=levyable,
        levy=levy, contributory=contributory, contributions=contributions,
        deductions=deductions,
        net=net_pay(gross, levy, contributions, deductions))
