"""What a caller may send about a timesheet."""

from pydantic import BaseModel, Field


class RecordHours(BaseModel):
    employee_id: str
    worked_on: str
    hours: int = Field(ge=0, le=24)
    element_id: str


class ApproveLine(BaseModel):
    approved: bool = True


class ListTimesheets(BaseModel):
    employee_id: str | None = None
    start: str | None = None
    end: str | None = None
    approved_only: bool = False
    limit: int | None = None
    offset: int | None = None


class TimesheetOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    worked_on: str
    hours: int
    element_id: str
    approved: bool

    @classmethod
    def of(cls, row) -> "TimesheetOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class HoursOut(BaseModel):
    employee_id: str
    start: str
    end: str
    hours: int
    days_worked: int
    by_element: dict[str, int]
