"""What comes back when gross pay is worked out."""

from pydantic import BaseModel


class GrossLineOut(BaseModel):
    element_id: str
    code: str
    name: str
    hours: int
    amount: int


class GrossOut(BaseModel):
    employee_id: str
    calendar_id: str
    period: int
    start: str
    end: str
    lines: list[GrossLineOut]
    gross: int
    taxable: int
    contributory: int
    pensionable: int
