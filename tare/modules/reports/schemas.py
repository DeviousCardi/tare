"""What comes back when a report is asked for."""

from pydantic import BaseModel


class WageBillOut(BaseModel):
    employer_id: str
    cost: int
    revenue: int
    paid: int
    by_period: dict[int, int]
    headcount_by_period: dict[int, int]
