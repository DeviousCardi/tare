"""What a caller may send about an employer, and what comes back."""

from pydantic import BaseModel, Field

from tare.common.dates import is_calendar_date
from tare.common.errors import refuse


class CalendarDay(str):
    """A `YYYY-MM-DD` day, refused by name rather than by schema noise."""


def a_day(value: str, what: str) -> str:
    if not is_calendar_date(value):
        raise refuse(f"{value} is not a calendar date")
    return value


class TakeOnEmployer(BaseModel):
    """Taking an employer onto the books."""

    name: str = Field(min_length=1, max_length=120)
    opened_on: str
    pay_day: int = Field(ge=1, le=31)
    reference: str | None = None


class CloseEmployer(BaseModel):
    """Taking an employer off them again."""

    closed_on: str


class ListEmployers(BaseModel):
    """Narrowing a listing of employers."""

    open_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class EmployerOut(BaseModel):
    id: str
    reference: str
    name: str
    opened_on: str
    closed_on: str | None
    pay_day: int

    @classmethod
    def of(cls, row) -> "EmployerOut":
        return cls(id=row.id, reference=row.reference, name=row.name,
                   opened_on=row.opened_on, closed_on=row.closed_on,
                   pay_day=row.pay_day)
