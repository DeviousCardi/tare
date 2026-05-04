"""What a caller may send about a filing."""

from pydantic import BaseModel, Field


class RaiseFiling(BaseModel):
    run_id: str
    period: int = Field(ge=1, le=53)
    period_end: str
    gross: int = Field(ge=0)
    levy: int = Field(ge=0)
    contributions: int = Field(ge=0)


class ListFilings(BaseModel):
    employer_id: str | None = None
    period: int | None = None
    limit: int | None = None
    offset: int | None = None


class FilingOut(BaseModel):
    id: str
    employer_id: str
    run_id: str
    period: int
    period_end: str
    due_on: str
    gross: int
    levy: int
    contributions: int

    @classmethod
    def of(cls, row) -> "FilingOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class FilingStateOut(BaseModel):
    filing_id: str
    owed: int
    due_on: str
    late: bool
    days_to_go: int
