"""What comes back when a register is read."""

from pydantic import BaseModel


class RegisterLineOut(BaseModel):
    key: str
    headcount: int
    gross: int
    levy: int
    contributions: int
    deductions: int
    net: int


class RegisterOut(BaseModel):
    run_id: str
    grouped_by: str
    lines: list[RegisterLineOut]
    totals: RegisterLineOut
