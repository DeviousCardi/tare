"""What a caller may send about a benefit award."""

from pydantic import BaseModel, Field


class AwardBenefit(BaseModel):
    employee_id: str
    class_id: str
    contribution: int = Field(default=0, ge=0)
    starts_on: str
    ends_on: str | None = None


class EndBenefit(BaseModel):
    ends_on: str


class ListBenefits(BaseModel):
    employee_id: str | None = None
    class_id: str | None = None
    held_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class BenefitOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    class_id: str
    contribution: int
    starts_on: str
    ends_on: str | None

    @classmethod
    def of(cls, row) -> "BenefitOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class BenefitValueOut(BaseModel):
    award_id: str
    days: int
    worth: int
    contribution: int
    taxable: int
