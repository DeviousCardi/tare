"""What a caller may send about an engagement."""

from pydantic import BaseModel, Field


class OpenEngagement(BaseModel):
    employer_id: str
    worker_name: str = Field(min_length=1, max_length=120)
    intermediary: str = Field(min_length=1, max_length=120)
    supervised: bool
    substitution_allowed: bool
    started_on: str


class EndEngagement(BaseModel):
    ended_on: str


class ListEngagements(BaseModel):
    employer_id: str | None = None
    running_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class EngagementOut(BaseModel):
    id: str
    employer_id: str
    worker_name: str
    intermediary: str
    supervised: bool
    substitution_allowed: bool
    started_on: str
    ended_on: str | None

    @classmethod
    def of(cls, row) -> "EngagementOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
