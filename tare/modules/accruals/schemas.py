"""What a caller may send about an accrual."""

from pydantic import BaseModel, Field


class RecordAccrual(BaseModel):
    employee_id: str
    year_starts_on: str
    period: int = Field(ge=1, le=53)
    hours_worked: int = Field(ge=0, le=1000)


class ListAccruals(BaseModel):
    employee_id: str | None = None
    year_starts_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class AccrualOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    year_starts_on: str
    period: int
    hours_worked: int
    hours_earned: int

    @classmethod
    def of(cls, row) -> "AccrualOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class EarnedOut(BaseModel):
    employee_id: str
    year_starts_on: str
    hours_worked: int
    hours_earned: int
    days_earned: int
