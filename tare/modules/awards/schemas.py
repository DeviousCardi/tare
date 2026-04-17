"""What a caller may send about an award."""

from pydantic import BaseModel, Field


class MakeAward(BaseModel):
    review_id: str
    employee_id: str
    basis: str
    amount: int = Field(gt=0)
    old_salary: int = Field(ge=0)


class ListAwards(BaseModel):
    review_id: str | None = None
    employee_id: str | None = None
    limit: int | None = None
    offset: int | None = None


class AwardOut(BaseModel):
    id: str
    review_id: str
    employee_id: str
    employer_id: str
    basis: str
    amount: int
    old_salary: int
    new_salary: int

    @classmethod
    def of(cls, row) -> "AwardOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ReviewCostOut(BaseModel):
    review_id: str
    awards: int
    cost: int
    average_share: int
