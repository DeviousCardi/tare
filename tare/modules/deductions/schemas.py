"""What a caller may send about a deduction instruction."""

from pydantic import BaseModel, Field


class InstructDeduction(BaseModel):
    employee_id: str
    element_id: str
    basis: str
    amount: int = Field(ge=0)
    priority: int = Field(default=50, ge=1, le=99)
    from_period: int = Field(ge=1, le=53)
    to_period: int | None = Field(default=None, ge=1, le=53)
    year_starts_on: str


class StopDeduction(BaseModel):
    to_period: int = Field(ge=1, le=53)


class ListDeductions(BaseModel):
    employee_id: str | None = None
    element_id: str | None = None
    due_in_period: int | None = None
    year_starts_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class DeductionOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    element_id: str
    basis: str
    amount: int
    priority: int
    from_period: int
    to_period: int | None
    year_starts_on: str

    @classmethod
    def of(cls, row) -> "DeductionOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class TakenOut(BaseModel):
    instruction_id: str
    element_id: str
    asked: int
    taken: int
    short: int


class RunOut(BaseModel):
    employee_id: str
    pay: int
    lines: list[TakenOut]
    total_taken: int
    total_short: int
