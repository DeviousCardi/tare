"""What comes back when net pay is worked out."""

from pydantic import BaseModel

from tare.modules.gross.schemas import GrossLineOut


class DeductionLineOut(BaseModel):
    element_id: str
    asked: int
    taken: int
    short: int


class NetOut(BaseModel):
    employee_id: str
    calendar_id: str
    period: int
    start: str
    end: str
    lines: list[GrossLineOut]
    deduction_lines: list[DeductionLineOut]
    gross: int
    taxable: int
    free_pay: int
    levyable: int
    levy: int
    contributory: int
    contributions: int
    deductions: int
    net: int
