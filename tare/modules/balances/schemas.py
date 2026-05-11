"""What a caller may send about a carried balance."""

from pydantic import BaseModel, Field


class HoldOver(BaseModel):
    employee_id: str
    element_id: str
    year_starts_on: str
    period: int = Field(ge=1, le=53)
    shortfall: int = Field(gt=0)


class ClearBalance(BaseModel):
    cleared_on: str


class ListBalances(BaseModel):
    employee_id: str | None = None
    element_id: str | None = None
    open_only: bool = False
    limit: int | None = None
    offset: int | None = None


class BalanceOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    element_id: str
    year_starts_on: str
    period: int
    shortfall: int
    carried: int
    cleared_on: str | None

    @classmethod
    def of(cls, row) -> "BalanceOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
