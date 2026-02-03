"""What a caller may send about a payroll run."""

from pydantic import BaseModel, Field


class OpenRun(BaseModel):
    employer_id: str
    calendar_id: str
    period: int = Field(ge=1, le=53)
    opened_on: str


class CommitRun(BaseModel):
    committed_on: str


class ListRuns(BaseModel):
    employer_id: str | None = None
    calendar_id: str | None = None
    period: int | None = None
    status: str | None = None
    limit: int | None = None
    offset: int | None = None


class RunOut(BaseModel):
    id: str
    employer_id: str
    calendar_id: str
    period: int
    status: str
    opened_on: str
    committed_on: str | None

    @classmethod
    def of(cls, row) -> "RunOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class RunTotalsOut(BaseModel):
    run_id: str
    status: str
    headcount: int
    gross: int
    revenue: int
    net: int
