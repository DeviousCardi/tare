"""Which centres can take cost, and how a figure is spread over them."""

from decimal import Decimal

from tare.common.errors import refuse
from tare.common.money import round_half_up
from tare.common.types import CostCentre


def sort_by_code(rows: list[CostCentre]) -> list[CostCentre]:
    return sorted(rows, key=lambda row: row.code)


def bookable(rows: list[CostCentre]) -> list[CostCentre]:
    """The centres a cost may still be booked to. A closed one may not."""
    return sort_by_code([row for row in rows if not row.closed])


def in_department(rows: list[CostCentre], department_id: str) -> list[CostCentre]:
    return sort_by_code([row for row in rows if row.department_id == department_id])


def share_across(amount: int, weights: list[int]) -> list[int]:
    """Spread a cost across centres in proportion to their weights.

    Each centre's share is its weight's part of the whole, in whole minor
    units.
    """
    if not weights:
        raise refuse("cannot spread a cost across no centres")
    if any(weight < 0 for weight in weights):
        raise refuse("cannot spread a cost across a negative weight")
    carried = sum(weights)
    if carried == 0:
        raise refuse("cannot spread a cost across weights that come to nothing")
    return [round_half_up(Decimal(amount) * Decimal(weight) / Decimal(carried))
            for weight in weights]
