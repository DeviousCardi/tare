"""What a caller may send about a leave request."""

from pydantic import BaseModel


class AskForLeave(BaseModel):
    employee_id: str
    starts_on: str
    ends_on: str
    asked_on: str


class DecideLeave(BaseModel):
    status: str


class ListLeave(BaseModel):
    employee_id: str | None = None
    status: str | None = None
    covering: str | None = None
    limit: int | None = None
    offset: int | None = None


class LeaveOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    starts_on: str
    ends_on: str
    asked_on: str
    status: str

    @classmethod
    def of(cls, row) -> "LeaveOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class TakenOut(BaseModel):
    employee_id: str
    start: str
    end: str
    days: int
