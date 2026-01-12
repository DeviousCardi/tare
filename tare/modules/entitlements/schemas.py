"""What a caller may send about an entitlement."""

from pydantic import BaseModel, Field


class GrantEntitlement(BaseModel):
    employee_id: str
    year_starts_on: str
    days: int = Field(ge=0, le=99)
    carried_in: int = Field(default=0, ge=0, le=99)


class ChangeEntitlement(BaseModel):
    days: int | None = Field(default=None, ge=0, le=99)
    carried_in: int | None = Field(default=None, ge=0, le=99)


class ListEntitlements(BaseModel):
    employee_id: str | None = None
    year_starts_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class EntitlementOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    year_starts_on: str
    days: int
    carried_in: int

    @classmethod
    def of(cls, row) -> "EntitlementOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class BalanceOut(BaseModel):
    employee_id: str
    year_starts_on: str
    year_ends_on: str
    earned: int
    carried_in: int
    available: int
    taken: int
    remaining: int
    carry_forward: int
