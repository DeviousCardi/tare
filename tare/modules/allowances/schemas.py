"""What a caller may send about an allowance."""

from pydantic import BaseModel, Field


class AwardAllowance(BaseModel):
    employee_id: str
    element_id: str
    amount: int = Field(ge=0)
    starts_on: str
    ends_on: str | None = None


class EndAllowance(BaseModel):
    ends_on: str


class ListAllowances(BaseModel):
    employee_id: str | None = None
    element_id: str | None = None
    standing_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class AllowanceOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    element_id: str
    amount: int
    starts_on: str
    ends_on: str | None

    @classmethod
    def of(cls, row) -> "AllowanceOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class StandingOut(BaseModel):
    employee_id: str
    on: str
    allowances: list[AllowanceOut]
    comes_to: int
    by_element: dict[str, int]
