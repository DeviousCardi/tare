"""Money arithmetic, in whole minor units.

Nothing in this service holds a fractional penny and nothing here returns a
float. Every function takes minor units and hands minor units back.

The rounding is **half up**, deliberately and explicitly. Python's own
`round()` rounds half to even, so `round(0.5)` is `0` and `round(1.5)` is `2` —
which is right for statistics and wrong for money, and wrong in a way that only
shows up on the halves. Everything here goes through `round_half_up`.
"""

from decimal import ROUND_HALF_UP, Decimal

from tare.common.errors import refuse


def round_half_up(value: Decimal | int | float) -> int:
    """The nearest whole minor unit, with a half going up and away from zero."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def total(values: list[int]) -> int:
    """What a run of figures comes to. An empty run comes to nothing."""
    return sum(values)


def apply_rate(amount: int, basis_points: int) -> int:
    """`amount` at a rate given in basis points — 2000 is twenty per cent.

    Rates are held in basis points rather than percentages so a rate of a
    quarter of a per cent is still a whole number and no table anywhere holds
    a fraction.
    """
    return round_half_up(Decimal(amount) * Decimal(basis_points) / Decimal(10000))


def per_thousand(amount: int, rate: int) -> int:
    """`amount` at a rate given per thousand, for the tables that quote that way."""
    return round_half_up(Decimal(amount) * Decimal(rate) / Decimal(1000))


def allocate(amount: int, parts: int) -> list[int]:
    """Split `amount` into `parts` whole pieces that sum back to `amount`.

    Largest remainder: every piece gets the floor, and the pennies left over go
    one each to the pieces with the largest remainder, earliest first. Dividing
    and rounding each piece instead loses or invents money — 100 over 3 comes
    to 99 that way, and a payroll that does it is a payroll that does not
    balance.
    """
    if parts <= 0:
        raise refuse("cannot split a figure into fewer than one part")
    sign = -1 if amount < 0 else 1
    magnitude = abs(amount)
    base, left_over = divmod(magnitude, parts)
    pieces = [base + (1 if i < left_over else 0) for i in range(parts)]
    return [sign * piece for piece in pieces]


def apportion(amount: int, weights: list[int]) -> list[int]:
    """Split `amount` across `weights`, in proportion, summing back to `amount`.

    Same largest-remainder rule as `allocate`, which is the degenerate case
    where every weight is equal. Weights that come to nothing are refused: the
    caller means something by an empty split and it is not this function's
    place to guess which.
    """
    if not weights:
        raise refuse("cannot apportion across no weights")
    if any(weight < 0 for weight in weights):
        raise refuse("cannot apportion across a negative weight")
    carried = total(weights)
    if carried == 0:
        raise refuse("cannot apportion across weights that come to nothing")

    exact = [Decimal(amount) * Decimal(weight) / Decimal(carried) for weight in weights]
    floors = [int(value // 1) for value in exact]
    left_over = amount - total(floors)
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - floors[i]), i))
    for i in range(left_over):
        floors[order[i % len(order)]] += 1
    return floors


def format_minor(amount: int) -> str:
    """For a payslip line. Two places, a thousands separator, minus in front."""
    sign = "-" if amount < 0 else ""
    whole, minor = divmod(abs(amount), 100)
    return f"{sign}{whole:,}.{minor:02d}"
