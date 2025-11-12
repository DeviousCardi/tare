"""What a caller may send about a relief."""

from pydantic import BaseModel, Field


class PublishRelief(BaseModel):
    code: str = Field(min_length=1, max_length=12)
    description: str = Field(min_length=1, max_length=120)
    basis: str
    amount: int = Field(ge=0)
    effective_from: str


class ListReliefs(BaseModel):
    code: str | None = None
    in_force_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class ReliefOut(BaseModel):
    id: str
    code: str
    description: str
    basis: str
    amount: int
    effective_from: str

    @classmethod
    def of(cls, row) -> "ReliefOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ReliefAppliedOut(BaseModel):
    code: str
    pay: int
    relieved: int
