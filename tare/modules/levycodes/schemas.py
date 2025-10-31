"""What a caller may send about a levy code."""

from pydantic import BaseModel, Field


class PublishLevyCode(BaseModel):
    code: str = Field(min_length=1, max_length=12)
    description: str = Field(min_length=1, max_length=120)
    annual_allowance: int = Field(ge=0)
    basis: str
    effective_from: str


class ListLevyCodes(BaseModel):
    code: str | None = None
    in_force_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class LevyCodeOut(BaseModel):
    id: str
    code: str
    description: str
    annual_allowance: int
    basis: str
    effective_from: str

    @classmethod
    def of(cls, row) -> "LevyCodeOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class FreePayOut(BaseModel):
    code: str
    frequency: str
    period: int
    free_pay: int
