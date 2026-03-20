"""What a caller may send about a payment instruction."""

from pydantic import BaseModel, Field


class IssuePayment(BaseModel):
    run_id: str
    employee_id: str
    amount: int = Field(gt=0)
    issued_on: str


class SettlePayment(BaseModel):
    settled_on: str


class FailPayment(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


class ListPayments(BaseModel):
    run_id: str | None = None
    employee_id: str | None = None
    status: str | None = None
    limit: int | None = None
    offset: int | None = None


class PaymentOut(BaseModel):
    id: str
    run_id: str
    employee_id: str
    employer_id: str
    account: str
    amount: int
    status: str
    issued_on: str
    settled_on: str | None

    @classmethod
    def of(cls, row) -> "PaymentOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class RunPaymentsOut(BaseModel):
    run_id: str
    settled: int
    failed: int
    outstanding: int
