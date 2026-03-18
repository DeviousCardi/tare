"""What a caller may send about a mandate."""

from pydantic import BaseModel, Field


class SetMandate(BaseModel):
    employee_id: str
    account: str
    holder: str = Field(min_length=1, max_length=120)
    starts_on: str


class EndMandate(BaseModel):
    ends_on: str


class ListMandates(BaseModel):
    employee_id: str | None = None
    standing_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class MandateOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    account: str
    holder: str
    starts_on: str
    ends_on: str | None

    @classmethod
    def of(cls, row) -> "MandateOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
