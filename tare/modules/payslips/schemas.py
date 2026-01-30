"""What comes back when a payslip is read."""

from pydantic import BaseModel


class PayslipLineOut(BaseModel):
    id: str
    element_id: str
    kind: str
    hours: int
    amount: int

    @classmethod
    def of(cls, row) -> "PayslipLineOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class PayslipOut(BaseModel):
    id: str
    run_id: str
    employee_id: str
    employer_id: str
    period: int
    start: str
    end: str
    gross: int
    taxable: int
    free_pay: int
    levy: int
    contributory: int
    contributions: int
    deductions: int
    net: int

    @classmethod
    def of(cls, row) -> "PayslipOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ListPayslips(BaseModel):
    employee_id: str | None = None
    run_id: str | None = None
    period: int | None = None
    limit: int | None = None
    offset: int | None = None


class PayslipWithLinesOut(BaseModel):
    payslip: PayslipOut
    lines: list[PayslipLineOut]
    payments: int
    deductions: int
    balances: bool
