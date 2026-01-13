"""What a caller may send about a suspension."""

from pydantic import BaseModel, Field


class SuspendDeduction(BaseModel):
    employee_id: str
    element_id: str
    reason: str
    from_period: int = Field(ge=1, le=53)
    year_starts_on: str


class LiftSuspension(BaseModel):
    to_period: int = Field(ge=1, le=53)


class ListSuspensions(BaseModel):
    employee_id: str | None = None
    element_id: str | None = None
    open_only: bool = False
    limit: int | None = None
    offset: int | None = None


class SuspensionOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    element_id: str
    reason: str
    from_period: int
    to_period: int | None
    year_starts_on: str

    @classmethod
    def of(cls, row) -> "SuspensionOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
