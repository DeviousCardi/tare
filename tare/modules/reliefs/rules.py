"""What a relief takes off, worked out on its own."""

from tare.common.effective import all_in_force_on, in_force_on
from tare.common.money import apply_rate
from tare.common.types import Relief

#: How a relief is quoted.
FLAT = "flat"
SHARE = "share"
BASES = (FLAT, SHARE)


def for_code(rows: list[Relief], code: str, day: str) -> Relief | None:
    return in_force_on([row for row in rows if row.code == code], day)


def every_relief_on(rows: list[Relief], day: str) -> list[Relief]:
    return all_in_force_on(rows, day, lambda row: row.code)


def relieved(row: Relief, pay: int) -> int:
    """What this relief takes off a figure of pay.

    A flat relief takes its own amount, or the whole of the pay if the pay is
    smaller — a relief never turns pay negative. A share takes its rate of the
    pay.
    """
    if pay <= 0:
        return 0
    if row.basis == SHARE:
        return apply_rate(pay, row.amount)
    return min(row.amount, pay)


def relieved_by_all(rows: list[Relief], pay: int) -> int:
    """What a run of reliefs takes off between them.

    Each is worked out on the **original** pay rather than on what the one
    before it left, so the order they are applied in cannot change the answer.
    The total is capped at the pay: reliefs reduce a figure to nothing and no
    further.
    """
    taken = sum(relieved(row, pay) for row in rows)
    return min(taken, max(0, pay))
