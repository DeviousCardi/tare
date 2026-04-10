"""What a caller may send about a loan plan."""

from pydantic import BaseModel, Field


class StartPlan(BaseModel):
    employee_id: str
    reference: str = Field(min_length=1, max_length=40)
    plan_type: str
    total: int = Field(gt=0)
    period_threshold: int = Field(ge=0)
    rate_basis_points: int = Field(gt=0, le=10000)
    started_on: str


class CollectOnPlan(BaseModel):
    amount: int = Field(gt=0)


class SettlePlan(BaseModel):
    settled_on: str


class ListPlans(BaseModel):
    employee_id: str | None = None
    live_only: bool = False
    limit: int | None = None
    offset: int | None = None


class PlanOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    reference: str
    plan_type: str
    total: int
    collected: int
    period_threshold: int
    rate_basis_points: int
    started_on: str
    settled_on: str | None

    @classmethod
    def of(cls, row) -> "PlanOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class DueOut(BaseModel):
    plan_id: str
    pay: int
    above_threshold: int
    due: int
    remaining: int
