"""What a caller may send about a run of service."""

from pydantic import BaseModel, Field


class RecordService(BaseModel):
    employee_id: str
    started_on: str
    reason: str = Field(min_length=1, max_length=200)


class EndService(BaseModel):
    ended_on: str


class ListService(BaseModel):
    employee_id: str | None = None
    limit: int | None = None
    offset: int | None = None


class ServiceOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    started_on: str
    ended_on: str | None
    reason: str

    @classmethod
    def of(cls, row) -> "ServiceOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ContinuityOut(BaseModel):
    employee_id: str
    continuous_from: str | None
    upto: str
    days: int
    years: int
