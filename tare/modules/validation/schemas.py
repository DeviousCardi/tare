"""What comes back when a run is checked."""

from pydantic import BaseModel


class FindingOut(BaseModel):
    check: str
    level: str
    subject: str
    detail: str


class CheckOut(BaseModel):
    run_id: str
    findings: list[FindingOut]
    blocking: int
    may_commit: bool
