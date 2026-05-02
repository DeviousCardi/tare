"""What a caller may send about a determination."""

from pydantic import BaseModel, Field


class DecideEngagement(BaseModel):
    engagement_id: str
    inside: bool
    fee: int = Field(ge=0)
    allowable_expenses: int = Field(default=0, ge=0)
    decided_on: str


class ListDeterminations(BaseModel):
    engagement_id: str | None = None
    employer_id: str | None = None
    inside_only: bool = False
    limit: int | None = None
    offset: int | None = None


class DeterminationOut(BaseModel):
    id: str
    engagement_id: str
    employer_id: str
    inside: bool
    fee: int
    allowable_expenses: int
    deemed_payment: int
    decided_on: str

    @classmethod
    def of(cls, row) -> "DeterminationOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
