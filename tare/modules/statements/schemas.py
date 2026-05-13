"""What a caller may send about a year-end statement."""

from pydantic import BaseModel


class DrawStatement(BaseModel):
    employee_id: str
    year_starts_on: str
    year_ends_on: str


class IssueStatement(BaseModel):
    issued_on: str


class ListStatements(BaseModel):
    employee_id: str | None = None
    year_starts_on: str | None = None
    issued_only: bool = False
    limit: int | None = None
    offset: int | None = None


class StatementOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    year_starts_on: str
    year_ends_on: str
    gross: int
    levy: int
    contributions: int
    net: int
    issued_on: str | None

    @classmethod
    def of(cls, row) -> "StatementOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
