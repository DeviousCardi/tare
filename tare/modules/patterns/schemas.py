"""What a caller may send about a working pattern."""

from pydantic import BaseModel, Field


class SetPattern(BaseModel):
    employee_id: str
    starts_on: str
    hours: list[int] = Field(min_length=7, max_length=7)


class EndPattern(BaseModel):
    ends_on: str


class ListPatterns(BaseModel):
    employee_id: str | None = None
    standing_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class PatternOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    starts_on: str
    ends_on: str | None
    hours: list[int]

    @classmethod
    def of(cls, row) -> "PatternOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ExpectedOut(BaseModel):
    employee_id: str
    start: str
    end: str
    hours: int
