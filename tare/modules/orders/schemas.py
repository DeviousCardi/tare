"""What a caller may send about an earnings order."""

from pydantic import BaseModel, Field


class ServeOrder(BaseModel):
    employee_id: str
    reference: str = Field(min_length=1, max_length=40)
    total: int = Field(gt=0)
    per_period: int = Field(gt=0)
    priority: int = Field(default=10, ge=1, le=99)
    made_on: str


class CollectOnOrder(BaseModel):
    amount: int = Field(gt=0)


class DischargeOrder(BaseModel):
    discharged_on: str


class ListOrders(BaseModel):
    employee_id: str | None = None
    live_only: bool = False
    limit: int | None = None
    offset: int | None = None


class OrderOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    reference: str
    total: int
    per_period: int
    collected: int
    priority: int
    made_on: str
    discharged_on: str | None

    @classmethod
    def of(cls, row) -> "OrderOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class OrderStateOut(BaseModel):
    order_id: str
    live: bool
    remaining: int
    due_now: int
    periods_left: int
