"""What a caller may send about a pay calendar."""

from pydantic import BaseModel, Field


class OpenCalendar(BaseModel):
    employer_id: str
    frequency: str
    year_starts_on: str
    periods: int | None = Field(default=None, ge=1, le=53)


class ListCalendars(BaseModel):
    employer_id: str | None = None
    frequency: str | None = None
    limit: int | None = None
    offset: int | None = None


class CalendarOut(BaseModel):
    id: str
    employer_id: str
    frequency: str
    year_starts_on: str
    periods: int

    @classmethod
    def of(cls, row) -> "CalendarOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class PeriodOut(BaseModel):
    calendar_id: str
    period: int
    start: str
    end: str
    pay_day: str
