"""What a caller may send about an exemption."""

from pydantic import BaseModel, Field


class GrantExemption(BaseModel):
    employee_id: str
    kind: str
    reason: str = Field(min_length=1, max_length=200)
    starts_on: str
    ends_on: str | None = None


class EndExemption(BaseModel):
    ends_on: str


class ListExemptions(BaseModel):
    employee_id: str | None = None
    kind: str | None = None
    standing_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class ExemptionOut(BaseModel):
    id: str
    employee_id: str
    kind: str
    reason: str
    starts_on: str
    ends_on: str | None

    @classmethod
    def of(cls, row) -> "ExemptionOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
