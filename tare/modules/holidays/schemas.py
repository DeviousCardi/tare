"""What a caller may send about the calendar."""

from pydantic import BaseModel, Field


class PublishHoliday(BaseModel):
    holiday_on: str
    name: str = Field(min_length=1, max_length=80)


class ListHolidays(BaseModel):
    year: int | None = None
    start: str | None = None
    end: str | None = None
    limit: int | None = None
    offset: int | None = None


class HolidayOut(BaseModel):
    id: str
    holiday_on: str
    name: str

    @classmethod
    def of(cls, row) -> "HolidayOut":
        return cls(id=row.id, holiday_on=row.holiday_on, name=row.name)


class WorkingDayOut(BaseModel):
    day: str
    is_working_day: bool
