"""Who is in a review, and what state it is in."""

from tare.common.types import Employee, PayReview


def sort_by_effective(rows: list[PayReview]) -> list[PayReview]:
    return sorted(rows, key=lambda row: (row.effective_from, row.id))


def is_open(row: PayReview) -> bool:
    """A review nobody has closed yet."""
    return row.closed_on is None


def population_of(row: PayReview, people: list[Employee]) -> list[Employee]:
    """Who the review covers.

    Everybody on the employer's books, in reference order.
    """
    return sorted([person for person in people
                   if person.employer_id == row.employer_id],
                  key=lambda person: person.reference)
