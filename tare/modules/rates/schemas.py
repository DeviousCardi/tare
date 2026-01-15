"""What a caller may send about a rate."""

from pydantic import BaseModel, Field


class SetRate(BaseModel):
    employee_id: str
    element_id: str
    basis: str
    amount: int = Field(ge=0)
    effective_from: str


class ListRates(BaseModel):
    employee_id: str | None = None
    element_id: str | None = None
    in_force_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class RateOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    element_id: str
    basis: str
    amount: int
    effective_from: str

    @classmethod
    def of(cls, row) -> "RateOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class AppliedOut(BaseModel):
    employee_id: str
    element_id: str
    hours: int
    amount: int
