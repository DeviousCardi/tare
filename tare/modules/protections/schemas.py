"""What a caller may send about a protected earnings floor."""

from pydantic import BaseModel, Field


class SetProtection(BaseModel):
    employee_id: str
    floor: int = Field(ge=0)
    starts_on: str
    ends_on: str | None = None


class EndProtection(BaseModel):
    ends_on: str


class ListProtections(BaseModel):
    employee_id: str | None = None
    standing_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class ProtectionOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    floor: int
    starts_on: str
    ends_on: str | None

    @classmethod
    def of(cls, row) -> "ProtectionOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ReachOut(BaseModel):
    employee_id: str
    pay: int
    floor: int
    available: int
    asked: int
    takeable: int
    breaches: bool
