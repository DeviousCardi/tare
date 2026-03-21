"""What a caller may send about an expense claim."""

from pydantic import BaseModel, Field


class MakeClaim(BaseModel):
    employee_id: str
    element_id: str
    kind: str = Field(min_length=1, max_length=40)
    amount: int = Field(gt=0)
    incurred_on: str
    claimed_on: str


class DecideClaim(BaseModel):
    status: str


class ListClaims(BaseModel):
    employee_id: str | None = None
    status: str | None = None
    start: str | None = None
    end: str | None = None
    limit: int | None = None
    offset: int | None = None


class ClaimOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    element_id: str
    kind: str
    amount: int
    incurred_on: str
    claimed_on: str
    status: str

    @classmethod
    def of(cls, row) -> "ClaimOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class OwedOut(BaseModel):
    employee_id: str
    comes_to: int
    by_kind: dict[str, int]
